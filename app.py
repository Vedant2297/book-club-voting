import hashlib
import hmac
import html
import re
import uuid

import pandas as pd
import requests
import streamlit as st
from supabase import create_client, Client


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Read Them To Filth",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SECRETS / CONNECTIONS
# ============================================================

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_PUBLISHABLE_KEY = st.secrets["supabase"]["publishable_key"]
SUPABASE_SECRET_KEY = st.secrets["supabase"]["secret_key"]

ADMIN_PASSWORD_HASH = st.secrets["admin"]["password_hash"]

GOOGLE_BOOKS_API_KEY = st.secrets["google"]["books_api_key"]


supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY,
)

admin_supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
)


# ============================================================
# SESSION STATE
# ============================================================

if "selected_books" not in st.session_state:
    st.session_state.selected_books = []

if "submitted_rounds" not in st.session_state:
    st.session_state.submitted_rounds = set()

if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False

if "current_view" not in st.session_state:
    st.session_state.current_view = "Vote"

if "info_book" not in st.session_state:
    st.session_state.info_book = None


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

/* ------------------------------------------------------------
   GLOBAL
------------------------------------------------------------ */

.stApp {
    background: #faf9f6;
}

.block-container {
    max-width: 1500px;
    padding-top: 3rem;
    padding-bottom: 4rem;
    padding-left: 2.5rem;
    padding-right: 2.5rem;
}

html,
body,
[class*="css"] {
    font-family:
        Inter,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}

h1,
h2,
h3 {
    letter-spacing: -0.035em;
}

header[data-testid="stHeader"] {
    background: transparent;
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}


/* ------------------------------------------------------------
   SIDEBAR
------------------------------------------------------------ */

section[data-testid="stSidebar"] {
    background:
        linear-gradient(
            180deg,
            #202223 0%,
            #181a1b 100%
        );

    border-right: none;
}

section[data-testid="stSidebar"] > div {
    padding-top: 2.5rem;
}

.club-name {
    color: #ffffff;
    font-size: 1.55rem;
    font-weight: 760;
    letter-spacing: -0.045em;
    line-height: 1.1;
    padding: 0 0.3rem 2rem 0.3rem;
}

.sidebar-admin {
    color: #ffffff;
    background: rgba(255,255,255,0.12);
    border-radius: 10px;
    padding: 0.85rem 1rem;
    font-weight: 650;
}

section[data-testid="stSidebar"] div.stButton > button {
    width: 100%;
    min-height: 50px;
    text-align: left;
    justify-content: flex-start;
    padding-left: 1rem;
    border-radius: 10px;
    margin-bottom: 0.35rem;
    font-weight: 650;
}

section[data-testid="stSidebar"] div.stButton > button[kind="secondary"] {
    background: transparent;
    border: 1px solid transparent;
    color: #efefeb;
}

section[data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.07);
    border-color: transparent;
    color: white;
}

section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
    background: rgba(255,255,255,0.13);
    border: 1px solid transparent;
    color: white;
}


/* ------------------------------------------------------------
   PAGE HEADER
------------------------------------------------------------ */

.round-label {
    font-size: 0.88rem;
    color: #333333;
    margin-bottom: 0.4rem;
    font-weight: 520;
}

.main-heading {
    font-size: 2.75rem;
    font-weight: 790;
    line-height: 1.03;
    letter-spacing: -0.055em;
    color: #151616;
    margin: 0;
}

.sub-heading {
    color: #737373;
    font-size: 1rem;
    margin-top: 0.8rem;
    margin-bottom: 2rem;
}


/* ------------------------------------------------------------
   BOOK CARDS
------------------------------------------------------------ */

.book-card {
    background: #ffffff;
    border: 1px solid #e5e3de;
    border-radius: 14px;
    padding: 1rem;
    margin-bottom: 0.55rem;
    height: 410px;
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
}

.book-cover-wrap {
    height: 285px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 0.9rem;
    overflow: hidden;
}

.book-cover {
    max-height: 275px;
    max-width: 185px;
    width: auto;
    height: auto;
    object-fit: contain;
    border-radius: 3px;
    box-shadow: 0 7px 20px rgba(0,0,0,0.10);
}

.book-title {
    font-weight: 720;
    font-size: 0.98rem;
    line-height: 1.25;
    color: #171717;
    text-align: center;
    margin-top: auto;
}

.book-author {
    text-align: center;
    color: #666662;
    font-size: 0.86rem;
    margin-top: 0.3rem;
    min-height: 22px;
}

.no-cover {
    width: 165px;
    height: 250px;
    background: #f1f0ec;
    border: 1px solid #e2e0db;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    color: #999994;
    font-size: 0.8rem;
    padding: 1rem;
    box-sizing: border-box;
}


/* ------------------------------------------------------------
   BOOK INFO
------------------------------------------------------------ */

.info-card {
    height: 410px;
    box-sizing: border-box;
    overflow-y: auto;
    background: #222424;
    color: #f8f7f2;
    border-radius: 14px;
    padding: 1.3rem;
    margin-bottom: 0.55rem;
}

.info-card h3 {
    color: #ffffff;
    margin: 0;
    font-size: 1.15rem;
    line-height: 1.2;
}

.info-author {
    color: #bcbcb7;
    font-size: 0.86rem;
    margin-top: 0.3rem;
    margin-bottom: 1.2rem;
}

.info-label {
    text-transform: uppercase;
    font-size: 0.64rem;
    letter-spacing: 0.09em;
    color: #999994;
    margin-top: 1rem;
    margin-bottom: 0.2rem;
}

.info-value {
    color: #f6f5f0;
    font-size: 0.88rem;
    line-height: 1.35;
}

.description {
    color: #deded9;
    font-size: 0.82rem;
    line-height: 1.5;
    margin-top: 0.3rem;
}


/* ------------------------------------------------------------
   SELECTION PANEL
------------------------------------------------------------ */

.selection-panel {
    background: #ffffff;
    border: 1px solid #e5e3de;
    border-radius: 14px;
    padding: 1.25rem;
    margin-bottom: 1.3rem;
}

.selection-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 720;
    font-size: 1rem;
    color: #222222;
    margin-bottom: 1rem;
}

.selection-count {
    color: #777772;
    font-size: 0.85rem;
}

.selection-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    border: 1px solid #e8e6e1;
    background: #faf9f6;
    border-radius: 10px;
    padding: 0.75rem;
    margin-bottom: 0.65rem;
    min-height: 58px;
    box-sizing: border-box;
}

.selection-number {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 31px;
    width: 31px;
    height: 31px;
    border-radius: 50%;
    background: #e5e4df;
    color: #242424;
    font-weight: 720;
    font-size: 0.83rem;
}

.selection-name {
    color: #333333;
    font-size: 0.86rem;
    line-height: 1.25;
}

.empty-selection {
    color: #9b9b96;
}


/* ------------------------------------------------------------
   BOOK OF THE MONTH RATING
------------------------------------------------------------ */

.month-book-section {
    margin-top: 3.5rem;
    padding-top: 2.5rem;
    border-top: 1px solid #dedcd6;
}

.month-book-eyebrow {
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 0.72rem;
    font-weight: 700;
    color: #777772;
    margin-bottom: 0.65rem;
}

.month-book-heading {
    text-align: center;
    font-size: 2rem;
    line-height: 1.1;
    font-weight: 780;
    letter-spacing: -0.045em;
    color: #171717;
    margin-bottom: 0.5rem;
}

.month-book-subheading {
    text-align: center;
    color: #777772;
    font-size: 0.95rem;
    margin-bottom: 2rem;
}

.month-book-card {
    background: #ffffff;
    border: 1px solid #e5e3de;
    border-radius: 16px;
    padding: 1.6rem;
    min-height: 330px;
    box-sizing: border-box;
}

.month-book-cover-wrap {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 275px;
}

.month-book-cover {
    width: auto;
    max-width: 190px;
    max-height: 285px;
    object-fit: contain;
    border-radius: 4px;
    box-shadow: 0 10px 28px rgba(0,0,0,0.13);
}

.month-book-title {
    font-size: 1.75rem;
    line-height: 1.1;
    font-weight: 760;
    letter-spacing: -0.04em;
    color: #171717;
    margin-top: 1rem;
}

.month-book-author {
    color: #777772;
    font-size: 0.95rem;
    margin-top: 0.45rem;
    margin-bottom: 2rem;
}

.month-book-question {
    font-size: 1.15rem;
    font-weight: 680;
    color: #222222;
    margin-bottom: 0.25rem;
}

.month-book-rating-help {
    color: #858580;
    font-size: 0.85rem;
    margin-bottom: 0.8rem;
}


/* ------------------------------------------------------------
   RESULTS
------------------------------------------------------------ */

.winner-card {
    background: #222424;
    color: white;
    border-radius: 14px;
    padding: 1.6rem;
    margin-bottom: 1.5rem;
}

.winner-label {
    color: #b8b8b3;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.09em;
}

.winner-title {
    font-size: 1.8rem;
    font-weight: 750;
    margin-top: 0.3rem;
}


/* ------------------------------------------------------------
   BUTTONS
------------------------------------------------------------ */

div.stButton > button {
    border-radius: 9px;
    min-height: 42px;
    font-weight: 620;
    box-shadow: none;
}

div.stButton > button[kind="primary"] {
    background: #222424;
    color: #ffffff;
    border: 1px solid #222424;
}

div.stButton > button[kind="primary"]:hover {
    background: #353737;
    border-color: #353737;
}

div.stButton > button:disabled {
    opacity: 0.48;
}


/* ------------------------------------------------------------
   MOBILE
------------------------------------------------------------ */

@media (max-width: 900px) {

    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
        padding-top: 2rem;
    }

    .main-heading {
        font-size: 2.1rem;
    }

    .book-card,
    .info-card {
        height: auto;
        min-height: 400px;
    }

    .book-cover-wrap {
        height: 260px;
    }

    .month-book-card {
        min-height: auto;
    }
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# GENERAL HELPERS
# ============================================================

def safe(value):
    if value is None:
        return ""

    return html.escape(
        str(value),
        quote=True,
    )


def clean_html(raw_html):
    if not raw_html:
        return ""

    text = re.sub(
        r"<[^>]+>",
        " ",
        str(raw_html),
    )

    text = html.unescape(text)

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def truncate(text, length=650):
    if not text:
        return "No description available."

    if len(text) <= length:
        return text

    return (
        text[:length]
        .rsplit(" ", 1)[0]
        + "…"
    )


def password_ok(password: str) -> bool:

    digest = hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()

    return hmac.compare_digest(
        digest,
        str(ADMIN_PASSWORD_HASH).strip(),
    )


# ============================================================
# GOOGLE BOOKS
# ============================================================

@st.cache_data(
    show_spinner=False,
    ttl=60 * 60 * 24 * 30,
)
def get_book_metadata(title, author):

    fallback = {
        "cover_url": None,
        "page_count": None,
        "primary_genre": None,
        "secondary_genre": None,
        "description": None,
    }

    try:

        query = f'intitle:"{title}"'

        if author:
            query += f' inauthor:"{author}"'

        response = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params={
                "q": query,
                "maxResults": 40,
                "printType": "books",
                "langRestrict": "en",
                "key": GOOGLE_BOOKS_API_KEY,
            },
            timeout=10,
        )

        response.raise_for_status()

        items = response.json().get(
            "items",
            [],
        )

        if not items:
            return fallback

        title_lower = (
            title
            .lower()
            .strip()
        )

        author_lower = (
            author
            .lower()
            .strip()
            if author
            else ""
        )

        candidates = []

        for item in items:

            info = item.get(
                "volumeInfo",
                {},
            )

            result_title = (
                info.get(
                    "title",
                    "",
                )
                .lower()
                .strip()
            )

            result_authors = [
                str(a)
                .lower()
                .strip()
                for a in info.get(
                    "authors",
                    [],
                )
            ]

            language = (
                info.get(
                    "language",
                    "",
                )
                .lower()
                .strip()
            )

            # Explicitly reject non-English editions.
            if (
                language
                and language != "en"
            ):
                continue

            score = 0

            # ------------------------------------------------
            # TITLE
            # ------------------------------------------------

            if (
                result_title
                == title_lower
            ):
                score += 50

            elif (
                title_lower
                in result_title
                or result_title
                in title_lower
            ):
                score += 25

            else:
                continue

            # ------------------------------------------------
            # AUTHOR
            # ------------------------------------------------

            if author_lower:

                if any(
                    author_lower == a
                    for a in result_authors
                ):
                    score += 50

                elif any(
                    author_lower in a
                    or a in author_lower
                    for a in result_authors
                ):
                    score += 25

                else:
                    continue

            # ------------------------------------------------
            # QUALITY
            # ------------------------------------------------

            if language == "en":
                score += 30

            if info.get("imageLinks"):
                score += 12

            if info.get("description"):
                score += 10

            if info.get("pageCount"):
                score += 5

            if info.get("categories"):
                score += 5

            candidates.append(
                (
                    score,
                    item,
                )
            )

        if not candidates:
            return fallback

        candidates.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        best_item = (
            candidates[0][1]
        )

        info = best_item.get(
            "volumeInfo",
            {},
        )

        # ----------------------------------------------------
        # COVER
        # ----------------------------------------------------

        image_links = info.get(
            "imageLinks",
            {},
        )

        cover_url = (
            image_links.get("extraLarge")
            or image_links.get("large")
            or image_links.get("medium")
            or image_links.get("small")
            or image_links.get("thumbnail")
            or image_links.get("smallThumbnail")
        )

        if cover_url:

            cover_url = (
                cover_url
                .replace(
                    "http://",
                    "https://",
                )
                .replace(
                    "&edge=curl",
                    "",
                )
            )

            if "zoom=" in cover_url:

                cover_url = re.sub(
                    r"zoom=\d+",
                    "zoom=2",
                    cover_url,
                )

        # ----------------------------------------------------
        # GENRES
        # ----------------------------------------------------

        categories = (
            info.get("categories")
            or []
        )

        primary_genre = (
            categories[0]
            if len(categories) >= 1
            else None
        )

        secondary_genre = (
            categories[1]
            if len(categories) >= 2
            else None
        )

        # ----------------------------------------------------
        # DESCRIPTION
        # ----------------------------------------------------

        description = clean_html(
            info.get("description")
        )

        return {
            "cover_url": cover_url,
            "page_count": info.get(
                "pageCount"
            ),
            "primary_genre": (
                primary_genre
            ),
            "secondary_genre": (
                secondary_genre
            ),
            "description": (
                description
            ),
        }

    except Exception as e:

        print(
            "Google Books error:",
            repr(e),
        )

        return fallback


# ============================================================
# DATABASE READS
# ============================================================

def get_active_round():

    response = (
        supabase
        .table("rounds")
        .select("*")
        .eq(
            "is_active",
            True,
        )
        .order(
            "created_at",
            desc=True,
        )
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def get_round_books(round_id):

    response = (
        supabase
        .table("round_books")
        .select("*")
        .eq(
            "round_id",
            round_id,
        )
        .order(
            "display_order"
        )
        .execute()
    )

    return response.data or []


def get_current_book(round_id):

    response = (
        supabase
        .table("current_books")
        .select("*")
        .eq(
            "round_id",
            round_id,
        )
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def get_votes(round_id):

    response = (
        admin_supabase
        .table("votes")
        .select(
            "id,"
            "submitted_at,"
            "round_id,"
            "rank_1,"
            "rank_2,"
            "rank_3,"
            "rating"
        )
        .eq(
            "round_id",
            round_id,
        )
        .order(
            "submitted_at"
        )
        .execute()
    )

    return pd.DataFrame(
        response.data or []
    )


def get_all_rounds():

    response = (
        supabase
        .table("rounds")
        .select("*")
        .order(
            "created_at",
            desc=True,
        )
        .execute()
    )

    return response.data or []


# ============================================================
# VOTING
# ============================================================

def save_vote(
    round_id,
    rank_1,
    rank_2,
    rank_3,
    rating,
):

    payload = {
        "id": str(
            uuid.uuid4()
        ),
        "round_id": round_id,
        "rank_1": rank_1,
        "rank_2": rank_2,
        "rank_3": rank_3,
        "rating": int(rating),
    }

    (
        supabase
        .table("votes")
        .insert(
            payload,
            returning="minimal",
        )
        .execute()
    )


def toggle_book(title):

    selected = list(
        st.session_state
        .selected_books
    )

    if title in selected:

        selected.remove(
            title
        )

    elif len(selected) < 3:

        selected.append(
            title
        )

    st.session_state.selected_books = (
        selected
    )


# ============================================================
# RESULTS CALCULATION
# ============================================================

def build_results(votes):

    if votes.empty:

        return pd.DataFrame(
            columns=[
                "Book",
                "Points",
                "Firsts",
                "Seconds",
                "Thirds",
            ]
        )

    books = (
        set(
            votes[
                "rank_1"
            ].dropna()
        )
        | set(
            votes[
                "rank_2"
            ].dropna()
        )
        | set(
            votes[
                "rank_3"
            ].dropna()
        )
    )

    rows = []

    for book in books:

        firsts = int(
            (
                votes["rank_1"]
                == book
            ).sum()
        )

        seconds = int(
            (
                votes["rank_2"]
                == book
            ).sum()
        )

        thirds = int(
            (
                votes["rank_3"]
                == book
            ).sum()
        )

        points = (
            firsts * 3
            + seconds * 2
            + thirds
        )

        rows.append(
            {
                "Book": book,
                "Points": points,
                "Firsts": firsts,
                "Seconds": seconds,
                "Thirds": thirds,
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(
            [
                "Points",
                "Firsts",
                "Seconds",
                "Book",
            ],
            ascending=[
                False,
                False,
                False,
                True,
            ],
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# ADMIN DATABASE FUNCTIONS
# ============================================================

def activate_round(round_id):

    (
        admin_supabase
        .table("rounds")
        .update(
            {
                "is_active": False
            }
        )
        .eq(
            "is_active",
            True,
        )
        .execute()
    )

    (
        admin_supabase
        .table("rounds")
        .update(
            {
                "is_active": True
            }
        )
        .eq(
            "id",
            round_id,
        )
        .execute()
    )


def archive_round(round_id):

    (
        admin_supabase
        .table("rounds")
        .update(
            {
                "is_active": False
            }
        )
        .eq(
            "id",
            round_id,
        )
        .execute()
    )


def create_round(
    round_name,
    current_title,
    current_author,
    nominations,
):

    round_id = str(
        uuid.uuid4()
    )

    # --------------------------------------------------------
    # CREATE ROUND
    # --------------------------------------------------------

    (
        admin_supabase
        .table("rounds")
        .insert(
            {
                "id": round_id,
                "name": round_name,
                "is_active": False,
            }
        )
        .execute()
    )

    # --------------------------------------------------------
    # CURRENT BOOK
    # --------------------------------------------------------

    current_metadata = (
        get_book_metadata(
            current_title,
            current_author,
        )
    )

    (
        admin_supabase
        .table("current_books")
        .insert(
            {
                "id": str(
                    uuid.uuid4()
                ),
                "round_id": (
                    round_id
                ),
                "title": (
                    current_title
                ),
                "author": (
                    current_author
                ),
                "cover_url": (
                    current_metadata.get(
                        "cover_url"
                    )
                ),
            }
        )
        .execute()
    )

    # --------------------------------------------------------
    # NOMINATIONS
    # --------------------------------------------------------

    rows = []

    for idx, book in enumerate(
        nominations
    ):

        metadata = (
            get_book_metadata(
                book["title"],
                book["author"],
            )
        )

        rows.append(
            {
                "id": str(
                    uuid.uuid4()
                ),
                "round_id": (
                    round_id
                ),
                "title": (
                    book["title"]
                ),
                "author": (
                    book["author"]
                ),
                "cover_url": (
                    metadata.get(
                        "cover_url"
                    )
                ),
                "page_count": (
                    metadata.get(
                        "page_count"
                    )
                ),
                "primary_genre": (
                    metadata.get(
                        "primary_genre"
                    )
                ),
                "secondary_genre": (
                    metadata.get(
                        "secondary_genre"
                    )
                ),
                "description": (
                    metadata.get(
                        "description"
                    )
                ),
                "display_order": (
                    idx + 1
                ),
            }
        )

    if rows:

        (
            admin_supabase
            .table("round_books")
            .insert(
                rows
            )
            .execute()
        )

    return round_id


# ============================================================
# ADMIN MODE
# ============================================================

admin_mode = (
    str(
        st.query_params.get(
            "admin",
            "",
        )
    ).lower()
    == "true"
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
<div class="club-name">
Read Them To Filth
</div>
""",
        unsafe_allow_html=True,
    )

    if admin_mode:

        st.markdown(
            """
<div class="sidebar-admin">
Admin
</div>
""",
            unsafe_allow_html=True,
        )

    else:

        vote_type = (
            "primary"
            if (
                st.session_state
                .current_view
                == "Vote"
            )
            else "secondary"
        )

        results_type = (
            "primary"
            if (
                st.session_state
                .current_view
                == "Results"
            )
            else "secondary"
        )

        if st.button(
            "Vote",
            key="sidebar_vote",
            use_container_width=True,
            type=vote_type,
        ):

            st.session_state.current_view = (
                "Vote"
            )

            st.rerun()

        if st.button(
            "Results",
            key="sidebar_results",
            use_container_width=True,
            type=results_type,
        ):

            st.session_state.current_view = (
                "Results"
            )

            st.rerun()


# ============================================================
# ACTIVE ROUND
# ============================================================

active_round = (
    get_active_round()
)


# ============================================================
# ADMIN PAGE
# ============================================================

if admin_mode:

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    if not st.session_state.admin_authed:

        st.markdown(
            """
<div class="round-label">
Private area
</div>

<div class="main-heading">
Admin
</div>

<div class="sub-heading">
Enter the admin password to continue.
</div>
""",
            unsafe_allow_html=True,
        )

        password = (
            st.text_input(
                "Admin password",
                type="password",
            )
        )

        if st.button(
            "Log in",
            type="primary",
        ):

            if password_ok(
                password
            ):

                st.session_state.admin_authed = (
                    True
                )

                st.rerun()

            else:

                st.error(
                    "Incorrect password."
                )

    # --------------------------------------------------------
    # ADMIN DASHBOARD
    # --------------------------------------------------------

    else:

        st.markdown(
            """
<div class="round-label">
Read Them To Filth
</div>

<div class="main-heading">
Admin
</div>

<div class="sub-heading">
Create rounds, manage voting and review results.
</div>
""",
            unsafe_allow_html=True,
        )

        if st.button(
            "Log out"
        ):

            st.session_state.admin_authed = (
                False
            )

            st.rerun()

        st.divider()

        # ----------------------------------------------------
        # CREATE ROUND
        # ----------------------------------------------------

        st.subheader(
            "Create new voting round"
        )

        with st.form(
            "create_round_form"
        ):

            round_name = (
                st.text_input(
                    "Round name",
                    placeholder=(
                        "October 2026"
                    ),
                )
            )

            current_title = (
                st.text_input(
                    "Current book title"
                )
            )

            current_author = (
                st.text_input(
                    "Current book author"
                )
            )

            st.markdown(
                "### Nominated books"
            )

            nomination_count = (
                st.number_input(
                    "Number of nominations",
                    min_value=3,
                    max_value=20,
                    value=6,
                    step=1,
                )
            )

            nominations = []

            for i in range(
                int(
                    nomination_count
                )
            ):

                c1, c2 = (
                    st.columns(2)
                )

                with c1:

                    title = (
                        st.text_input(
                            f"Book {i + 1} title",
                            key=(
                                f"new_title_{i}"
                            ),
                        )
                    )

                with c2:

                    author = (
                        st.text_input(
                            f"Book {i + 1} author",
                            key=(
                                f"new_author_{i}"
                            ),
                        )
                    )

                nominations.append(
                    {
                        "title": (
                            title.strip()
                        ),
                        "author": (
                            author.strip()
                        ),
                    }
                )

            activate_now = (
                st.checkbox(
                    "Make this the active voting round",
                    value=True,
                )
            )

            submitted = (
                st.form_submit_button(
                    "Create round",
                    type="primary",
                )
            )

            if submitted:

                cleaned = [
                    book
                    for book
                    in nominations
                    if book["title"]
                ]

                if not (
                    round_name.strip()
                ):

                    st.error(
                        "Enter a round name."
                    )

                elif not (
                    current_title.strip()
                ):

                    st.error(
                        "Enter the current book."
                    )

                elif len(
                    cleaned
                ) < 3:

                    st.error(
                        "Enter at least 3 nominated books."
                    )

                else:

                    with st.spinner(
                        "Finding book covers and metadata..."
                    ):

                        new_id = (
                            create_round(
                                round_name.strip(),
                                current_title.strip(),
                                current_author.strip(),
                                cleaned,
                            )
                        )

                    if activate_now:

                        activate_round(
                            new_id
                        )

                    st.session_state.selected_books = []
                    st.session_state.info_book = None

                    st.success(
                        "Voting round created."
                    )

                    st.rerun()

        # ----------------------------------------------------
        # EXISTING ROUNDS
        # ----------------------------------------------------

        st.divider()

        st.subheader(
            "Existing rounds"
        )

        rounds = (
            get_all_rounds()
        )

        if not rounds:

            st.caption(
                "No rounds have been created yet."
            )

        else:

            round_options = {}

            for r in rounds:

                label = r["name"]

                if r[
                    "is_active"
                ]:

                    label += (
                        " • ACTIVE"
                    )

                round_options[
                    label
                ] = r

            selected_label = (
                st.selectbox(
                    "Choose a round",
                    list(
                        round_options.keys()
                    ),
                )
            )

            selected_round = (
                round_options[
                    selected_label
                ]
            )

            selected_round_id = (
                selected_round[
                    "id"
                ]
            )

            rbooks = (
                get_round_books(
                    selected_round_id
                )
            )

            rcurrent = (
                get_current_book(
                    selected_round_id
                )
            )

            rvotes = (
                get_votes(
                    selected_round_id
                )
            )

            status = (
                "Active"
                if selected_round[
                    "is_active"
                ]
                else "Archived"
            )

            st.write(
                f"**Status:** {status}"
            )

            st.write(
                f"**Votes submitted:** {len(rvotes)}"
            )

            action1, action2 = (
                st.columns(2)
            )

            with action1:

                if not selected_round[
                    "is_active"
                ]:

                    if st.button(
                        "Make active",
                        use_container_width=True,
                    ):

                        activate_round(
                            selected_round_id
                        )

                        st.session_state.selected_books = []
                        st.session_state.info_book = None

                        st.rerun()

            with action2:

                if selected_round[
                    "is_active"
                ]:

                    if st.button(
                        "Close voting",
                        use_container_width=True,
                    ):

                        archive_round(
                            selected_round_id
                        )

                        st.rerun()

            if rcurrent:

                current_author = (
                    rcurrent.get(
                        "author"
                    )
                    or ""
                )

                current_text = (
                    rcurrent["title"]
                )

                if current_author:

                    current_text += (
                        f" — {current_author}"
                    )

                st.write(
                    f"**Current book:** {current_text}"
                )

            if rbooks:

                rdf = (
                    pd.DataFrame(
                        rbooks
                    )
                )

                desired_columns = [
                    "display_order",
                    "title",
                    "author",
                    "page_count",
                    "primary_genre",
                    "secondary_genre",
                ]

                available_columns = [
                    col
                    for col
                    in desired_columns
                    if col
                    in rdf.columns
                ]

                st.dataframe(
                    rdf[
                        available_columns
                    ],
                    hide_index=True,
                    use_container_width=True,
                )

            if not rvotes.empty:

                st.markdown(
                    "### Results"
                )

                st.dataframe(
                    build_results(
                        rvotes
                    ),
                    hide_index=True,
                    use_container_width=True,
                )

                st.metric(
                    "Average book rating",
                    (
                        f"{rvotes['rating'].mean():.1f}"
                        " / 5"
                    ),
                )


# ============================================================
# PUBLIC VOTE PAGE
# ============================================================

elif (
    st.session_state.current_view
    == "Vote"
):

    if not active_round:

        st.markdown(
            """
<div class="main-heading">
Voting is closed
</div>

<div class="sub-heading">
Check back when the next round opens.
</div>
""",
            unsafe_allow_html=True,
        )

    else:

        round_id = (
            active_round[
                "id"
            ]
        )

        round_name = (
            active_round[
                "name"
            ]
        )

        books = (
            get_round_books(
                round_id
            )
        )

        current_book = (
            get_current_book(
                round_id
            )
        )

        # ----------------------------------------------------
        # REMOVE STALE SELECTIONS
        # ----------------------------------------------------

        valid_titles = {
            book["title"]
            for book in books
        }

        st.session_state.selected_books = [
            title
            for title
            in st.session_state.selected_books
            if title
            in valid_titles
        ]

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        header_html = f"""
<div class="round-label">{safe(round_name)}</div>
<div class="main-heading">Vote for our next read</div>
<div class="sub-heading">Select your top 3 books in order of preference. Click More info to learn about a book.</div>
"""

        st.markdown(
            header_html,
            unsafe_allow_html=True,
        )

        # ----------------------------------------------------
        # ALREADY VOTED
        # ----------------------------------------------------

        if (
            round_id
            in st.session_state
            .submitted_rounds
        ):

            st.success(
                "Your vote has been submitted."
            )

            if st.button(
                "View results",
                type="primary",
            ):

                st.session_state.current_view = (
                    "Results"
                )

                st.rerun()

        # ----------------------------------------------------
        # NOT ENOUGH BOOKS
        # ----------------------------------------------------

        elif len(
            books
        ) < 3:

            st.warning(
                "This voting round doesn't have enough nominated books yet."
            )

        # ----------------------------------------------------
        # VOTING
        # ----------------------------------------------------

        else:

            main_col, selection_col = (
                st.columns(
                    [
                        4.2,
                        1.25,
                    ],
                    gap="large",
                )
            )

            # =================================================
            # BOOK GRID
            # =================================================

            with main_col:

                cols_per_row = 4

                for start in range(
                    0,
                    len(books),
                    cols_per_row,
                ):

                    row_books = books[
                        start:
                        start
                        + cols_per_row
                    ]

                    cols = (
                        st.columns(
                            cols_per_row,
                            gap="small",
                        )
                    )

                    for (
                        col_index,
                        col,
                    ) in enumerate(
                        cols
                    ):

                        if (
                            col_index
                            >= len(
                                row_books
                            )
                        ):
                            continue

                        book = (
                            row_books[
                                col_index
                            ]
                        )

                        with col:

                            book_id = (
                                book[
                                    "id"
                                ]
                            )

                            title = (
                                book[
                                    "title"
                                ]
                            )

                            author = (
                                book.get(
                                    "author"
                                )
                                or ""
                            )

                            showing_info = (
                                st.session_state
                                .info_book
                                == book_id
                            )

                            # ---------------------------------
                            # INFO VIEW
                            # ---------------------------------

                            if showing_info:

                                pages = (
                                    book.get(
                                        "page_count"
                                    )
                                    or "Unknown"
                                )

                                primary = (
                                    book.get(
                                        "primary_genre"
                                    )
                                    or "Not listed"
                                )

                                secondary = (
                                    book.get(
                                        "secondary_genre"
                                    )
                                )

                                genres = (
                                    safe(
                                        primary
                                    )
                                )

                                if secondary:

                                    genres += (
                                        " · "
                                        + safe(
                                            secondary
                                        )
                                    )

                                description = (
                                    truncate(
                                        book.get(
                                            "description"
                                        )
                                    )
                                )

                                info_html = f"""
<div class="info-card">
<h3>{safe(title)}</h3>
<div class="info-author">{safe(author)}</div>
<div class="info-label">Pages</div>
<div class="info-value">{safe(pages)}</div>
<div class="info-label">Genre</div>
<div class="info-value">{genres}</div>
<div class="info-label">About the book</div>
<div class="description">{safe(description)}</div>
</div>
"""

                                st.markdown(
                                    info_html,
                                    unsafe_allow_html=True,
                                )

                                if st.button(
                                    "Back to cover",
                                    key=(
                                        f"back_{book_id}"
                                    ),
                                    use_container_width=True,
                                ):

                                    st.session_state.info_book = (
                                        None
                                    )

                                    st.rerun()

                            # ---------------------------------
                            # COVER VIEW
                            # ---------------------------------

                            else:

                                cover = (
                                    book.get(
                                        "cover_url"
                                    )
                                )

                                if cover:

                                    cover_content = f"""
<img class="book-cover" src="{safe(cover)}" alt="{safe(title)} book cover">
"""

                                else:

                                    cover_content = """
<div class="no-cover">
Cover unavailable
</div>
"""

                                card_html = f"""
<div class="book-card">
<div class="book-cover-wrap">
{cover_content}
</div>
<div class="book-title">{safe(title)}</div>
<div class="book-author">{safe(author)}</div>
</div>
"""

                                st.markdown(
                                    card_html,
                                    unsafe_allow_html=True,
                                )

                                if st.button(
                                    "More info",
                                    key=(
                                        f"info_{book_id}"
                                    ),
                                    use_container_width=True,
                                ):

                                    st.session_state.info_book = (
                                        book_id
                                    )

                                    st.rerun()

                            # ---------------------------------
                            # SELECT
                            # ---------------------------------

                            selected = (
                                title
                                in st.session_state
                                .selected_books
                            )

                            selected_count = (
                                len(
                                    st.session_state
                                    .selected_books
                                )
                            )

                            if selected:

                                rank = (
                                    st.session_state
                                    .selected_books
                                    .index(
                                        title
                                    )
                                    + 1
                                )

                                rank_labels = {
                                    1: "1st choice",
                                    2: "2nd choice",
                                    3: "3rd choice",
                                }

                                if st.button(
                                    rank_labels[
                                        rank
                                    ],
                                    key=(
                                        f"remove_{book_id}"
                                    ),
                                    use_container_width=True,
                                ):

                                    toggle_book(
                                        title
                                    )

                                    st.rerun()

                            else:

                                if st.button(
                                    "Select",
                                    key=(
                                        f"select_{book_id}"
                                    ),
                                    type="primary",
                                    use_container_width=True,
                                    disabled=(
                                        selected_count
                                        >= 3
                                    ),
                                ):

                                    toggle_book(
                                        title
                                    )

                                    st.rerun()

            # =================================================
            # SELECTION PANEL
            # =================================================

            with selection_col:

                selected = list(
                    st.session_state
                    .selected_books
                )

                rows_html = ""

                for index in range(3):

                    if (
                        index
                        < len(
                            selected
                        )
                    ):

                        selection_text = (
                            safe(
                                selected[
                                    index
                                ]
                            )
                        )

                        name_class = (
                            "selection-name"
                        )

                    else:

                        selection_text = (
                            "No selection yet"
                        )

                        name_class = (
                            "selection-name "
                            "empty-selection"
                        )

                    rows_html += f"""
<div class="selection-row">
<div class="selection-number">{index + 1}</div>
<div class="{name_class}">{selection_text}</div>
</div>
"""

                selection_html = f"""
<div class="selection-panel">
<div class="selection-header">
<span>Your selections</span>
<span class="selection-count">{len(selected)} / 3</span>
</div>
{rows_html}
</div>
"""

                st.markdown(
                    selection_html,
                    unsafe_allow_html=True,
                )

            # =================================================
            # BOOK OF THE MONTH RATING
            # =================================================

            st.markdown(
                """
<div class="month-book-section">
<div class="month-book-eyebrow">Book of the month</div>
<div class="month-book-heading">How was this month's read?</div>
<div class="month-book-subheading">Give the current book a rating before submitting your vote.</div>
</div>
""",
                unsafe_allow_html=True,
            )

            rating = None

            if current_book:

                current_title = (
                    current_book.get(
                        "title"
                    )
                    or ""
                )

                current_author = (
                    current_book.get(
                        "author"
                    )
                    or ""
                )

                current_cover = (
                    current_book.get(
                        "cover_url"
                    )
                )

                rating_outer_left, rating_area, rating_outer_right = (
                    st.columns(
                        [
                            0.7,
                            4,
                            0.7,
                        ]
                    )
                )

                with rating_area:

                    rating_left, rating_right = (
                        st.columns(
                            [
                                1,
                                2.2,
                            ],
                            gap="large",
                        )
                    )

                    # -----------------------------------------
                    # CURRENT BOOK COVER
                    # -----------------------------------------

                    with rating_left:

                        if current_cover:

                            cover_html = f"""
<div class="month-book-card">
<div class="month-book-cover-wrap">
<img
    class="month-book-cover"
    src="{safe(current_cover)}"
    alt="{safe(current_title)} book cover"
>
</div>
</div>
"""

                        else:

                            cover_html = """
<div class="month-book-card">
<div class="month-book-cover-wrap">
<div class="no-cover">
Cover unavailable
</div>
</div>
</div>
"""

                        st.markdown(
                            cover_html,
                            unsafe_allow_html=True,
                        )

                    # -----------------------------------------
                    # RATING
                    # -----------------------------------------

                    with rating_right:

                        book_details_html = f"""
<div class="month-book-card">
<div class="month-book-title">{safe(current_title)}</div>
<div class="month-book-author">{safe(current_author)}</div>
<div class="month-book-question">What did you think?</div>
<div class="month-book-rating-help">Choose a rating from 1 to 5.</div>
</div>
"""

                        st.markdown(
                            book_details_html,
                            unsafe_allow_html=True,
                        )

                        rating = (
                            st.radio(
                                "Rate this month's book",
                                options=[
                                    1,
                                    2,
                                    3,
                                    4,
                                    5,
                                ],
                                format_func=lambda x: (
                                    f"{x}  "
                                    + "★" * x
                                    + "☆" * (
                                        5 - x
                                    )
                                ),
                                index=None,
                                horizontal=True,
                                label_visibility=(
                                    "collapsed"
                                ),
                                key=(
                                    f"rating_{round_id}"
                                ),
                            )
                        )

            # =================================================
            # SUBMIT
            # =================================================

            selected = list(
                st.session_state
                .selected_books
            )

            ready = (
                len(
                    selected
                ) == 3
                and rating
                is not None
            )

            st.write("")

            submit_left, submit_middle, submit_right = (
                st.columns(
                    [
                        1.5,
                        2,
                        1.5,
                    ]
                )
            )

            with submit_middle:

                if st.button(
                    "Submit votes",
                    type="primary",
                    use_container_width=True,
                    disabled=(
                        not ready
                    ),
                    key="submit_public_vote",
                ):

                    save_vote(
                        round_id,
                        selected[0],
                        selected[1],
                        selected[2],
                        rating,
                    )

                    (
                        st.session_state
                        .submitted_rounds
                        .add(
                            round_id
                        )
                    )

                    st.session_state.selected_books = []
                    st.session_state.info_book = None
                    st.session_state.current_view = (
                        "Results"
                    )

                    st.rerun()


# ============================================================
# RESULTS PAGE
# ============================================================

else:

    if not active_round:

        st.markdown(
            """
<div class="main-heading">
Results
</div>

<div class="sub-heading">
There is no active voting round at the moment.
</div>
""",
            unsafe_allow_html=True,
        )

    else:

        round_id = (
            active_round[
                "id"
            ]
        )

        votes = (
            get_votes(
                round_id
            )
        )

        results = (
            build_results(
                votes
            )
        )

        results_header = f"""
<div class="round-label">{safe(active_round['name'])}</div>
<div class="main-heading">Results</div>
<div class="sub-heading">Live results from the current voting round.</div>
"""

        st.markdown(
            results_header,
            unsafe_allow_html=True,
        )

        if votes.empty:

            st.info(
                "No votes have been submitted yet."
            )

        else:

            winner = (
                results.iloc[0]
            )

            winner_html = f"""
<div class="winner-card">
<div class="winner-label">Current leader</div>
<div class="winner-title">{safe(winner['Book'])}</div>
</div>
"""

            st.markdown(
                winner_html,
                unsafe_allow_html=True,
            )

            display_results = (
                results.rename(
                    columns={
                        "Firsts": "1st",
                        "Seconds": "2nd",
                        "Thirds": "3rd",
                    }
                )
            )

            st.dataframe(
                display_results,
                hide_index=True,
                use_container_width=True,
            )

            st.caption(
                "Scoring: 1st choice = 3 points, "
                "2nd choice = 2 points, and "
                "3rd choice = 1 point. "
                "Ties are broken by the number "
                "of first-place votes, then "
                "second-place votes."
            )

            st.divider()

            metric1, metric2 = (
                st.columns(2)
            )

            with metric1:

                st.metric(
                    "Average book rating",
                    (
                        f"{votes['rating'].mean():.1f}"
                        " / 5"
                    ),
                )

            with metric2:

                st.metric(
                    "Votes submitted",
                    len(
                        votes
                    ),
                )