# Book Club Voting App — Secure Admin Setup

## Public URL
`https://YOUR-APP.streamlit.app`

Shows only Vote + Results.

After someone submits, the app redirects them to Results.

## Private Admin URL
`https://YOUR-APP.streamlit.app/?admin=true`

The Admin interface is hidden unless this query parameter is present and still requires the admin password.

## Supabase security model
- Publishable key: normal voting/results only.
- Secret key: admin database writes only.
- The secret key is stored in Streamlit secrets and must NEVER be committed to GitHub.
- Row Level Security permits anonymous users to read poll configuration and insert votes.
- Raw ballot rows are not publicly readable; aggregate results are calculated server-side.
- Anonymous users cannot create/edit/close voting rounds.

## Setup
1. Create a fresh Supabase project.
2. Run `supabase_setup.sql` in SQL Editor.
3. Get the Project URL, publishable key, and secret key from Supabase.
4. Run `python3 make_admin_hash.py` locally and choose your admin password.
5. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
6. Fill in all four secret values.
7. Install dependencies and run locally.
8. Push everything EXCEPT `.streamlit/secrets.toml` to GitHub.
9. Deploy in Streamlit Community Cloud and paste the same secrets into Advanced settings.

## Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
