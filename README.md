<p align="center">
 <h2 align="center">Hadith Every Hour</h2>
 <p align="center">📖 A bot that posts a Hadith every hour on Twitter & Facebook</p>
 <p align="center"><i>(Every 6 hours for now to avoid spamming)</i></p>
</p>
<p align="center">
  Follow on Twitter <a href="https://twitter.com/HadithEveryHour">@HadithEveryHour</a> & Facebook <a href="https://www.facebook.com/HadithEveryHour">@HadithEveryHour</a>
</p>


## Status
[![Tweet](https://github.com/Ananto30/hadith-every-hour/actions/workflows/tweet.yml/badge.svg)](https://github.com/Ananto30/hadith-every-hour/actions/workflows/tweet.yml)
[![Post to Facebook](https://github.com/Ananto30/hadith-every-hour/actions/workflows/post_to_facebook.yml/badge.svg)](https://github.com/Ananto30/hadith-every-hour/actions/workflows/post_to_facebook.yml)

Currently posting the Hadiths from Sahih al-Bukhari in serial.

## Concept
It's really simple. GitHub action is written in <a href="/.github/workflows/tweet_hadith.yml">this</a> file. You can notice a scheduler - 
```
on:
  schedule:
    - cron: "0 */6 * * *"
```
And the rest of the process is self explanatory.

A tracker is used to put the latest posted Hadith number in the `hadith_track.json` file. 

API's are from this project - https://github.com/Ananto30/ask-hadith

## Facebook token refresh

Page tokens cannot be exchanged directly. This repository keeps a long-lived **user** token encrypted in `resources/fb_token.enc` and derives the Page token from it. A daily workflow (`refresh_facebook_token.yml`) checks both tokens. When the user token is within 14 days of expiry it is exchanged for a fresh long-lived token; when the Page token is within 14 days of expiry it is re-derived. The new state is encrypted and only `resources/fb_token.enc` is committed.

Refresh decisions use `expires_at` from `/debug_token`. `data_access_expires_at` is a separate ~90-day data-access window and is intentionally ignored; it is not the token's expiry.

One-time setup:

1. Generate a Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
2. Add the repository secrets `FB_APP_ID`, `FB_APP_SECRET`, `FB_PAGE_ID`, `TOKEN_ENCRYPTION_KEY`, and `FB_USER_TOKEN`.
   - `FB_USER_TOKEN` must have the `pages_show_list` and `pages_manage_posts` permissions, and the user must have a role on the Page. You can get one from the Graph API Explorer by selecting your app, adding those permissions, and logging in as a Page admin. A short-lived token is fine for setup; it is exchanged for a long-lived one immediately. A Business Manager system-user token with the Page assigned also works, and a never-expiring system-user token is left untouched.
   - `FB_PAGE_TOKEN` is only a bootstrap fallback for posting. You can delete it after the refresh workflow commits the encrypted state file.
   - `FB_USER_TOKEN` is only needed to initialize or recover. The rotated user token is stored, encrypted, in the state file.
3. Run the **Refresh Facebook token** workflow manually once. It creates and commits `resources/fb_token.enc`.
4. Keep `FB_APP_ID`, `FB_APP_SECRET`, `FB_PAGE_ID`, and `TOKEN_ENCRYPTION_KEY` — they are needed by the refresh workflow.

If you start with a non-expiring Page token, the state is page-only. Adding `FB_USER_TOKEN` later upgrades it automatically on the next run.

If the user token expires or is revoked, or if `TOKEN_ENCRYPTION_KEY` was changed, set a new `FB_USER_TOKEN` and run the workflow manually with **Replace stored tokens using FB_USER_TOKEN** checked. Force bootstrap overwrites the old state, including when the encryption key changed. Tokens can still be revoked by Meta at any time, so the scheduled workflow acts as a health check as well.


## Contribution
Feel free to contribute by creating issues or submitting pull requests. Any improvements, bug fixes, or suggestions for better handling of Hadith posting are welcome.
