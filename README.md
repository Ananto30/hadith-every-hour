<p align="center">
 <h2 align="center">Hadith Every Hour</h2>
 <p align="center">📖 A bot that posts a Hadith every hour on Twitter & Facebook</p>
 <p align="center"><i>(Every 6 hours for now to avoid spamming)</i></p>
</p>
<p align="center">
  Follow on Twitter <a href="https://twitter.com/HadithEveryHour">@HadithEveryHour</a> & Facebook <a href="https://www.facebook.com/HadithEveryHour">@HadithEveryHour</a>
</p>


### Status
[![Tweet](https://github.com/Ananto30/hadith-every-hour/actions/workflows/tweet.yml/badge.svg)](https://github.com/Ananto30/hadith-every-hour/actions/workflows/tweet.yml)
[![Post to Facebook](https://github.com/Ananto30/hadith-every-hour/actions/workflows/post_to_facebook.yml/badge.svg)](https://github.com/Ananto30/hadith-every-hour/actions/workflows/post_to_facebook.yml)

Currently posting the Hadiths from Sahih al-Bukhari in serial.

### Concept
It's really simple. GitHub action is written in <a href="/.github/workflows/tweet_hadith.yml">this</a> file. You can notice a scheduler - 
```
on:
  schedule:
    - cron: "0 */6 * * *"
```
And the rest of the process is self explanatory.

A tracker is used to put the latest posted Hadith number in the `hadith_track.json` file. 

API's are from this project - https://github.com/Ananto30/ask-hadith

### Flow
```
Get last Tweeted Hadith number from tracker
                    ⭣
          Get Hadith from API 
                    ⭣
      Make chunks for long Hadith
                    ⭣
   Limit chunks for very long Hadith 
                    ⭣
        Tweet and comment chunks
                    ⭣
       Format and post on Facebook
                    ⭣
              Update tracker
```

### Contribution
There can be a different approach of Tweeting (as Twitter has character limits on each post) or Hadith Selection, please create an issue and let's discuss about that.
