import hashlib
import hmac
import uuid
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
from supabase import create_client, Client

st.set_page_config(
    page_title="Book Club",
    page_icon="📚",
    layout="wide",
)

# ------------------------------------------------------------
# CONNECTIONS
# ------------------------------------------------------------
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_PUBLISHABLE_KEY = st.secrets["supabase"]["publishable_key"]
SUPABASE_SECRET_KEY = st.secrets["supabase"]["secret_key"]
ADMIN_PASSWORD_HASH = st.secrets["admin"]["password_hash"]

# Public client: used for normal voting/results and constrained by RLS.
supabase: Client = create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)

# Admin client: secret key is stored server-side only in Streamlit secrets.
# It bypasses RLS and is used only after the app's admin password gate.
admin_supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)


# ------------------------------------------------------------
# STYLING
# ------------------------------------------------------------
st.markdown(
    """
    <style>
        .block-container {
            max-width: 1150px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }

        .book-meta {
            min-height: 85px;
        }

        .rank-chip {
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 999px;
            background: rgba(127,127,127,0.14);
            font-weight: 700;
            margin-bottom: 0.4rem;
        }

        .selection-box {
            padding: 0.85rem 1rem;
            border-radius: 14px;
            background: rgba(127,127,127,0.08);
            margin-bottom: 0.4rem;
        }

        .small-muted {
            opacity: 0.7;
            font-size: 0.92rem;
        }

        .admin-box {
            padding: 1rem;
            border-radius: 14px;
            background: rgba(127,127,127,0.08);
            margin-bottom: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=60 * 60 * 24 * 30)
def get_cover_url(title, author):
    try:
        params = {
            "title": title,
            "author": author or "",
            "limit": 1,
            "fields": "key,title,author_name,cover_i",
        }
        response = requests.get(
            "https://openlibrary.org/search.json",
            params=params,
            timeout=8,
        )
        response.raise_for_status()
        docs = response.json().get("docs", [])

        if docs and docs[0].get("cover_i"):
            return f"https://covers.openlibrary.org/b/id/{docs[0]['cover_i']}-L.jpg"
    except Exception:
        pass

    return "https://placehold.co/420x640?text=No+Cover"


def password_ok(password: str) -> bool:
    digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(digest, ADMIN_PASSWORD_HASH)


def get_active_round():
    response = (
        supabase.table("rounds")
        .select("*")
        .eq("is_active", True)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def get_round_books(round_id):
    response = (
        supabase.table("round_books")
        .select("*")
        .eq("round_id", round_id)
        .order("display_order")
        .execute()
    )
    return response.data or []


def get_current_book(round_id):
    response = (
        supabase.table("current_books")
        .select("*")
        .eq("round_id", round_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def get_votes(round_id):
    response = (
        admin_supabase.table("votes")
        .select("id,submitted_at,round_id,rank_1,rank_2,rank_3,rating")
        .eq("round_id", round_id)
        .order("submitted_at")
        .execute()
    )
    return pd.DataFrame(response.data or [])


def save_vote(round_id, rank_1, rank_2, rank_3, rating):
    payload = {
        "id": str(uuid.uuid4()),
        "round_id": round_id,
        "rank_1": rank_1,
        "rank_2": rank_2,
        "rank_3": rank_3,
        "rating": int(rating),
    }
    supabase.table("votes").insert(
    payload,
    returning="minimal"
).execute()


def get_all_rounds():
    response = (
        supabase.table("rounds")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []

def activate_round(round_id):
    # Deactivate all currently active rounds
    admin_supabase.table("rounds").update(
        {"is_active": False}
    ).eq("is_active", True).execute()

    # Activate the selected round
    admin_supabase.table("rounds").update(
        {"is_active": True}
    ).eq("id", round_id).execute()


def archive_round(round_id):
    admin_supabase.table("rounds").update({"is_active": False}).eq("id", round_id).execute()


def create_round(round_name, current_title, current_author, nominations):
    round_id = str(uuid.uuid4())

    admin_supabase.table("rounds").insert({
        "id": round_id,
        "name": round_name,
        "is_active": False,
    }).execute()

    admin_supabase.table("current_books").insert({
        "id": str(uuid.uuid4()),
        "round_id": round_id,
        "title": current_title,
        "author": current_author,
        "cover_url": get_cover_url(current_title, current_author),
    }).execute()

    rows = []
    for idx, book in enumerate(nominations):
        rows.append({
            "id": str(uuid.uuid4()),
            "round_id": round_id,
            "title": book["title"],
            "author": book["author"],
            "cover_url": get_cover_url(book["title"], book["author"]),
            "display_order": idx + 1,
        })

    if rows:
        admin_supabase.table("round_books").insert(rows).execute()

    return round_id


def update_round_books(round_id, current_title, current_author, nominations):
    admin_supabase.table("current_books").delete().eq("round_id", round_id).execute()
    admin_supabase.table("round_books").delete().eq("round_id", round_id).execute()

    admin_supabase.table("current_books").insert({
        "id": str(uuid.uuid4()),
        "round_id": round_id,
        "title": current_title,
        "author": current_author,
        "cover_url": get_cover_url(current_title, current_author),
    }).execute()

    rows = []
    for idx, book in enumerate(nominations):
        rows.append({
            "id": str(uuid.uuid4()),
            "round_id": round_id,
            "title": book["title"],
            "author": book["author"],
            "cover_url": get_cover_url(book["title"], book["author"]),
            "display_order": idx + 1,
        })

    if rows:
        admin_supabase.table("round_books").insert(rows).execute()


def build_results(votes):
    if votes.empty:
        return pd.DataFrame(columns=["Book", "Points", "Firsts", "Seconds", "Thirds"])

    books = set(votes["rank_1"]) | set(votes["rank_2"]) | set(votes["rank_3"])
    rows = []

    for book in books:
        firsts = int((votes["rank_1"] == book).sum())
        seconds = int((votes["rank_2"] == book).sum())
        thirds = int((votes["rank_3"] == book).sum())
        points = firsts * 3 + seconds * 2 + thirds

        rows.append({
            "Book": book,
            "Points": points,
            "Firsts": firsts,
            "Seconds": seconds,
            "Thirds": thirds,
        })

    return (
        pd.DataFrame(rows)
        .sort_values(["Points", "Firsts", "Seconds"], ascending=[False, False, False])
        .reset_index(drop=True)
    )


# ------------------------------------------------------------
# SESSION STATE
# ------------------------------------------------------------
if "selected_books" not in st.session_state:
    st.session_state.selected_books = []

if "submitted_rounds" not in st.session_state:
    st.session_state.submitted_rounds = set()

if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False

if "current_view" not in st.session_state:
    st.session_state.current_view = "Vote"


def toggle_book(title):
    selected = st.session_state.selected_books

    if title in selected:
        selected.remove(title)
    elif len(selected) < 3:
        selected.append(title)

    st.session_state.selected_books = selected


def rank_label(title):
    if title not in st.session_state.selected_books:
        return None

    rank = st.session_state.selected_books.index(title) + 1
    return {
        1: "🥇 1st choice",
        2: "🥈 2nd choice",
        3: "🥉 3rd choice",
    }[rank]


# ------------------------------------------------------------
# APP
# ------------------------------------------------------------
st.title("📚 Book Club")

active_round = get_active_round()

# Admin is intentionally hidden from normal users.
# Only URLs containing ?admin=true expose the Admin view.
admin_mode = str(st.query_params.get("admin", "")).lower() == "true"

if admin_mode:
    allowed_views = ["Admin"]
    st.session_state.current_view = "Admin"
else:
    allowed_views = ["Vote", "Results"]

    if st.session_state.current_view not in allowed_views:
        st.session_state.current_view = "Vote"

    view = st.segmented_control(
        "Navigation",
        allowed_views,
        default=st.session_state.current_view,
        label_visibility="collapsed",
    )

    if view != st.session_state.current_view:
        st.session_state.current_view = view



# ------------------------------------------------------------
# PUBLIC VOTE
# ------------------------------------------------------------
if st.session_state.current_view == "Vote":
    if not active_round:
        st.info("Voting is currently closed. Check back when the next round opens.")
    else:
        round_id = active_round["id"]
        round_name = active_round["name"]
        books = get_round_books(round_id)
        current_book = get_current_book(round_id)

        st.caption(f"Current round: {round_name}")

        if round_id in st.session_state.submitted_rounds:
            st.success("Your vote has been submitted ✓")
        elif len(books) < 3:
            st.warning("This voting round is not ready yet.")
        else:
            st.header("Choose our next book")
            st.write(
                "Pick **three books in order**. Your first selection becomes your 1st choice, "
                "your second becomes 2nd, and your third becomes 3rd."
            )

            selected_count = len(st.session_state.selected_books)
            st.progress(selected_count / 3, text=f"{selected_count} of 3 selected")

            cols_per_row = 3

            for start in range(0, len(books), cols_per_row):
                row_books = books[start:start + cols_per_row]
                cols = st.columns(cols_per_row)

                for col, book in zip(cols, row_books):
                    with col:
                        st.image(book["cover_url"] or get_cover_url(book["title"], book["author"]), use_container_width=True)

                        st.markdown(
                            f"""
                            <div class="book-meta">
                                <strong>{book['title']}</strong><br>
                                <span class="small-muted">{book.get('author') or ''}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        label = rank_label(book["title"])

                        if label:
                            st.markdown(f'<div class="rank-chip">{label}</div>', unsafe_allow_html=True)
                            st.button(
                                "Remove",
                                key=f"remove_{round_id}_{book['id']}",
                                use_container_width=True,
                                on_click=toggle_book,
                                args=(book["title"],),
                            )
                        else:
                            st.button(
                                "Select",
                                key=f"select_{round_id}_{book['id']}",
                                use_container_width=True,
                                disabled=selected_count >= 3,
                                on_click=toggle_book,
                                args=(book["title"],),
                            )

            st.divider()
            st.subheader("Your ranking")

            if st.session_state.selected_books:
                rank_names = ["🥇 First", "🥈 Second", "🥉 Third"]
                for idx, title in enumerate(st.session_state.selected_books):
                    st.markdown(
                        f'<div class="selection-box"><strong>{rank_names[idx]}:</strong> {title}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No books selected yet.")

            st.divider()

            if current_book:
                st.header("How was this month’s book?")

                left, right = st.columns([1, 2])

                with left:
                    st.image(
                        current_book["cover_url"] or get_cover_url(current_book["title"], current_book["author"]),
                        use_container_width=True,
                    )

                with right:
                    st.subheader(current_book["title"])
                    st.caption(current_book.get("author") or "")
                    rating_display = st.radio(
                        "Rating",
                        ["★", "★★", "★★★", "★★★★", "★★★★★"],
                        horizontal=True,
                        index=None,
                        label_visibility="collapsed",
                    )

                rating = len(rating_display) if rating_display else None
            else:
                rating = None
                st.warning("The current book has not been configured.")

            st.divider()

            ready = len(st.session_state.selected_books) == 3 and rating is not None

            if st.button(
                "Submit anonymous vote",
                type="primary",
                use_container_width=True,
                disabled=not ready,
            ):
                save_vote(
                    round_id,
                    st.session_state.selected_books[0],
                    st.session_state.selected_books[1],
                    st.session_state.selected_books[2],
                    rating,
                )
                st.session_state.submitted_rounds.add(round_id)
                st.session_state.selected_books = []
                st.session_state.current_view = "Results"
                st.rerun()


# ------------------------------------------------------------
# RESULTS
# ------------------------------------------------------------
if st.session_state.current_view == "Results":
    if not active_round:
        st.info("There is no active voting round.")
    else:
        round_id = active_round["id"]
        votes = get_votes(round_id)
        results = build_results(votes)
        current_book = get_current_book(round_id)

        st.header(f"Results · {active_round['name']}")

        if votes.empty:
            st.info("No votes have been submitted yet.")
        else:
            winner = results.iloc[0]
            st.subheader(f"🏆 Current leader: {winner['Book']}")
            st.caption("Tie-breakers: most 1st-place votes, then most 2nd-place votes.")

            st.dataframe(
                results.rename(
                    columns={
                        "Firsts": "🥇",
                        "Seconds": "🥈",
                        "Thirds": "🥉",
                    }
                ),
                hide_index=True,
                use_container_width=True,
            )

            if current_book is not None:
                st.divider()
                st.subheader(f"{current_book['title']} rating")
                st.metric("Average rating", f"{votes['rating'].mean():.1f} / 5")
                st.caption(f"{len(votes)} anonymous vote{'s' if len(votes) != 1 else ''} submitted.")


# ------------------------------------------------------------
# ADMIN
# ------------------------------------------------------------
if admin_mode and st.session_state.current_view == "Admin":
    if not st.session_state.admin_authed:
        st.header("Admin login")
        password = st.text_input("Admin password", type="password")

        if st.button("Log in", type="primary"):
            if password_ok(password):
                st.session_state.admin_authed = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    else:
        st.header("Admin")
        st.caption("Private admin mode")
        st.caption("Create voting rounds, edit books, activate a month, and review archived rounds.")

        if st.button("Log out"):
            st.session_state.admin_authed = False
            st.rerun()

        st.divider()

        rounds = get_all_rounds()

        st.subheader("Create new voting round")

        with st.form("create_round_form"):
            round_name = st.text_input("Round name", placeholder="September 2026")
            current_title = st.text_input("Current book title")
            current_author = st.text_input("Current book author")

            st.write("Nominated books")
            nomination_count = st.number_input(
                "Number of nominations",
                min_value=3,
                max_value=20,
                value=6,
                step=1,
            )

            nominations = []
            for i in range(int(nomination_count)):
                c1, c2 = st.columns(2)
                with c1:
                    title = st.text_input(f"Book {i+1} title", key=f"new_title_{i}")
                with c2:
                    author = st.text_input(f"Book {i+1} author", key=f"new_author_{i}")
                nominations.append({"title": title.strip(), "author": author.strip()})

            activate_now = st.checkbox("Make this the active voting round", value=True)

            submitted = st.form_submit_button("Create round", type="primary")

            if submitted:
                cleaned = [b for b in nominations if b["title"]]

                if not round_name.strip() or not current_title.strip() or len(cleaned) < 3:
                    st.error("Enter a round name, current book, and at least 3 nominated books.")
                else:
                    new_id = create_round(
                        round_name.strip(),
                        current_title.strip(),
                        current_author.strip(),
                        cleaned,
                    )

                    if activate_now:
                        activate_round(new_id)

                    st.success("Voting round created.")
                    st.session_state.current_view = "Admin"
                    st.rerun()

        st.divider()

        st.subheader("Existing rounds")

        rounds = get_all_rounds()

        if not rounds:
            st.caption("No rounds yet.")
        else:
            round_options = {
                f"{r['name']} {'• ACTIVE' if r['is_active'] else ''}": r
                for r in rounds
            }

            selected_label = st.selectbox("Choose a round", list(round_options.keys()))
            selected_round = round_options[selected_label]
            selected_round_id = selected_round["id"]

            rbooks = get_round_books(selected_round_id)
            rcurrent = get_current_book(selected_round_id)
            rvotes = get_votes(selected_round_id)

            st.markdown(
                f"""
                <div class="admin-box">
                    <strong>{selected_round['name']}</strong><br>
                    Status: {'Active' if selected_round['is_active'] else 'Archived'}<br>
                    Votes: {len(rvotes)}
                </div>
                """,
                unsafe_allow_html=True,
            )

            c1, c2 = st.columns(2)

            with c1:
                if not selected_round["is_active"]:
                    if st.button("Make active", use_container_width=True):
                        activate_round(selected_round_id)
                        st.session_state.selected_books = []
                        st.success("Round activated.")
                        st.session_state.current_view = "Admin"
                        st.rerun()

            with c2:
                if selected_round["is_active"]:
                    if st.button("Close voting", use_container_width=True):
                        archive_round(selected_round_id)
                        st.success("Voting closed.")
                        st.session_state.current_view = "Admin"
                        st.rerun()

            st.subheader("Round details")

            if rcurrent:
                st.write(f"**Current book:** {rcurrent['title']} — {rcurrent.get('author') or ''}")

            if rbooks:
                st.dataframe(
                    pd.DataFrame(rbooks)[["display_order", "title", "author"]],
                    hide_index=True,
                    use_container_width=True,
                )

            if not rvotes.empty:
                st.subheader("Archived/current results")
                st.dataframe(build_results(rvotes), hide_index=True, use_container_width=True)

                if rcurrent:
                    st.metric("Current book average rating", f"{rvotes['rating'].mean():.1f} / 5")
