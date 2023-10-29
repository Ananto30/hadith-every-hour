class Twitter:
    tracker_file = "resources/hadith_track_twitter.json"

    consumer_key = "API_KEY"
    consumer_secret = "API_SECRET"
    access_token = "ACCESS_TOKEN"
    access_token_secret = "ACCESS_TOKEN_SECRET"

    char_limit = 260  # 280 - 20 (link)
    total_thread_char_limit = 4 * char_limit


class Facebook:
    tracker_file = "resources/hadith_track_fb.json"

    app_id = "FB_APP_ID"
    app_secret = "FB_APP_SECRET"
    page_id = "FB_PAGE_ID"
    page_token = "FB_PAGE_TOKEN"
    token_encryption_key = "TOKEN_ENCRYPTION_KEY"
