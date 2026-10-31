# Publishing Elevate Plate on the App Store: your checklist

These are the steps only you can do (they involve your Apple ID, payments, legal
agreements or your accounts). Everything else is already set up in the code.

The order matters: the slow steps (Apple enrollment) come first, so start them today.

**Expect:** enrollment approval 1–2 days (sometimes up to a week), App Review 1–2 days
per submission, and it's common to get rejected once and resubmit after a fix.

---

## Step 1: Push the code, then claim your data (today, ~5 min)

1. In a terminal in the project folder, run `git push`.
2. Wait for Vercel to show **Ready**, then open https://elevate-plate.vercel.app.
3. **Create your account right away.** The first account created on the live site takes
   ownership of all the recipes and plans that existed before accounts were added, so
   make sure that's you.

## Step 2: Enroll in the Apple Developer Program (today, ~20 min + waiting)

1. Make sure your Apple ID has **two-factor authentication** on (iPhone: Settings → your
   name → Sign-In & Security).
2. Go to https://developer.apple.com/programs/enroll/ and choose **Enroll as an
   individual** (your legal name will be shown as the seller on the App Store).
3. Pay the **$99/year** fee. Apple may ask you to verify your identity with a photo ID in
   the **Apple Developer** app.
4. Wait for the "Welcome to the Apple Developer Program" email.

## Step 3: Run the test build (anytime, no Apple account needed, ~15 min)

This proves the iPhone app compiles, using a free Mac that GitHub provides.

1. On GitHub, open your repo → **Actions** → **iOS app** → **Run workflow**.
2. Leave **"Sign and upload"** unchecked and click **Run workflow**.
3. A green check means the iPhone app builds. If it's red, open the run, copy the red
   error, and send it to Claude.

## Step 4: Pick your app's bundle ID (after enrollment, ~5 min)

A bundle ID is your app's permanent unique name, like `com.yourname.elevateplate`.
**It can't be changed after release.**

1. https://developer.apple.com/account → **Certificates, Identifiers & Profiles** →
   **Identifiers** → **+** → **App IDs** → **App**.
2. Description: `Elevate Plate`. Bundle ID: **Explicit**, e.g. `com.yourname.elevateplate`.
   No extra capabilities are needed. Click **Register**.
3. In GitHub: repo → **Settings** → **Secrets and variables** → **Actions** →
   **Variables** tab → **New repository variable**: name `IOS_BUNDLE_ID`, value your bundle ID.

## Step 5: Create the app in App Store Connect (~10 min)

1. https://appstoreconnect.apple.com → **Apps** → **+** → **New App**.
2. Platform **iOS**; Name **Elevate Plate** (if it's taken, try "Elevate Plate: Meal
   Planner"); language **English (U.S.)**; Bundle ID: the one from Step 4; SKU:
   `elevateplate001`; User Access: **Full Access**.
3. Accept any agreements shown under **Business** (free apps only need the basic one).

## Step 6: Create an API key so GitHub can upload builds (~10 min)

1. App Store Connect → **Users and Access** → **Integrations** → **App Store Connect API**
   → **Team Keys** → **+**. Name it `GitHub`, Access **Admin** (needed so the build can
   create signing certificates for you). Click **Generate**.
2. **Download the key file (`AuthKey_XXXXXXXX.p8`) now. Apple only lets you download it
   once.** Note the **Key ID** and the **Issuer ID** shown on that page.
3. Find your **Team ID**: https://developer.apple.com/account → **Membership details**.
4. In GitHub: repo → **Settings** → **Secrets and variables** → **Actions** → **Secrets**
   tab → **New repository secret**, four times:

   | Name | Value |
   | --- | --- |
   | `APPLE_TEAM_ID` | Your Team ID (10 characters) |
   | `ASC_KEY_ID` | The Key ID |
   | `ASC_ISSUER_ID` | The Issuer ID (a long ID with dashes) |
   | `ASC_KEY_P8` | Open the `.p8` file in Notepad and paste **everything**, including the `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----` lines |

   Never commit the `.p8` file to the repo or share it.

## Step 7: Build, upload and test on your iPhone (~30 min)

1. GitHub → **Actions** → **iOS app** → **Run workflow** → check **"Sign and upload"**,
   version `1.0.0` → **Run workflow**.
2. When it's green, wait 10–30 minutes for Apple to process it. You'll get an email.
3. App Store Connect → your app → **TestFlight**. Add yourself under **Internal Testing**.
4. Install **TestFlight** from the App Store on your iPhone, accept the invite, install
   Elevate Plate, and try everything: sign up, plan a week, share the list, turn on the
   shopping reminder (account menu), and use it in airplane mode.
5. If the upload step fails, send the red error to Claude. The first signed build often
   needs one small fix.

## Step 8: Fill in your contact email (~2 min)

`frontend/privacy.html` and `frontend/support.html` say
`REPLACE-WITH-YOUR-CONTACT-EMAIL`. Tell Claude the email you want to use for app support
(it will be public), or replace it yourself, then push.

## Step 9: Get a TheMealDB supporter key (before public release)

TheMealDB's free key is for "development or educational use". Their terms say you
"must become a supporter if releasing publicly on an appstore".

1. Become a supporter at https://www.themealdb.com (they link to the options).
2. In Vercel: your project → **Settings** → **Environment Variables** → add
   `MEALDB_API_KEY` = your supporter key → **Save**, then redeploy.

## Step 10: Fill in the App Store listing (~45 min)

In App Store Connect → your app → the **1.0 Prepare for Submission** page. Copy the
text from [LISTING.md](LISTING.md):

- Promotional text, description, keywords, support URL, privacy policy URL.
- **Screenshots** (required): at least 3 for **iPhone 6.9"** (1320 × 2868). Take them on
  your iPhone (side button + volume up) while using the TestFlight build. Claude can also
  prepare them at the right size from the web app if you ask.
- **App Privacy** (left menu): answer using the table in LISTING.md.
- **Age Rating**: answer "None" to everything → **4+**.
- **Category**: Food & Drink (secondary: Lifestyle). **Price**: Free.
- **App Review Information**: tick **Sign-in required** and give Apple a demo account
  (create a separate one on the live site, e.g. `review@...`, with a few recipes and a
  planned week). Paste the review notes from LISTING.md.
- **Build**: select the build you uploaded in Step 7.

## Step 11: Submit for review

1. Click **Add for Review** → **Submit to App Review**.
2. Watch your email. If Apple rejects it, the message in **App Store Connect →
   Resolution Center** explains why. Paste it to Claude and it will help fix it.
3. When approved, click **Release** (or set it to release automatically).

## Later: updating the app

- **Website:** every `git push` updates https://elevate-plate.vercel.app automatically.
- **iPhone app:** changes reach iPhone users only when you run the **iOS app** workflow
  with a higher version (e.g. `1.0.1`), then submit that build for review.
- The website and the app share the same accounts and data.
