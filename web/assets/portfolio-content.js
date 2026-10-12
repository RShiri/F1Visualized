/* Portfolio content for the shared brand kit (https://rshiri.github.io/assets/brand/brand.js):
   - window.RS_ABOUT: the "About this project" panel, in English and Hebrew.
   - window.RS_I18N: Hebrew for the dashboard's UI chrome. Keys are the exact trimmed English
     text nodes / title attributes; data (driver, team and race names, numbers) stays as is. */
(function () {
  window.RS_ABOUT = {
    en: {
      title: "F1 Visualized",
      intro: "A Formula 1 season dashboard for 2022–2026 plus a Python pipeline that turns a race's lap-by-lap timing into broadcast-style replay videos. Everything runs on public data with no API key, and the site is static: it is rebuilt and redeployed by GitHub Actions.",
      sections: [
        { h: "What it is",
          p: "Two parts share one repository. The <b>dashboard</b> (this page) covers five seasons with five views: Overview, Standings, Calendar, Results and Stats, and a season switch at the top. The <b>video pipeline</b> scrapes the most recent completed Grand Prix and renders two 1280×720 MP4 animations: a position-battle \"race\" where every car slides between position lanes lap by lap, and a classic position-by-lap bump chart, which can also be stitched side by side into one in-sync video." },
        { h: "Data sources and volume",
          p: "<code>fetch_season.py</code> builds one JSON file per season from two public sources: the <b>calendar</b> from <code>fastf1.get_event_schedule</code>, and <b>results, standings, grid positions, fastest laps and pit stops</b> from the open-source <b>f1db</b> dataset (its source YAML on GitHub). The committed snapshot holds 114 scheduled rounds across 2022–2026 and roughly 2,000 classified result rows. A scheduled race with no result yet is shown as <b>TBC</b> rather than invented." },
        { h: "Pipeline and automation",
          p: "A GitHub Actions workflow re-fetches 2025 and 2026 every Tuesday and Friday at 06:00 UTC (after race weekends), on every push and on demand, then publishes the <code>web/</code> folder to GitHub Pages. If the data source is unreachable the committed data is deployed instead, so the site always builds. A second, on-demand workflow runs the video pipeline: <code>scraper.py</code> finds the latest race whose timing is published, extracts position, tyre compound, pit stops and Virtual Safety Car laps per driver per lap, and two matplotlib engines render the videos with ffmpeg." },
        { h: "Methods behind the numbers",
          p: "<b>Season stats</b> aggregate every completed round: wins, podiums, poles, starts, average grid and finish, net places gained grid → flag, points finishes, DNFs and Driver of the Day awards. <b>Stop (s)</b> is an estimate: f1db records only the full pit-lane time, which is dominated by each circuit's lane length, so the race's fastest stop is treated as the shared drive-through and subtracted (the quickest stop is floored at 2.0 s), and the median is shown. <b>Team colours</b> that sit too close together (Red Bull, Racing Bulls and Williams are all blue) are checked with a CIE76 ΔE colour-difference test each season and the lower-ranked one is nudged apart." },
        { h: "How to read the views",
          p: "<b>Overview</b>: the two championship leaders with a bar showing their share of leader + runner-up points, the next-race countdown, the last podium and the top five. <b>Standings</b>: full tables with team-coloured points bars. <b>Calendar</b>: every round with its status; a completed card opens that race. <b>Results</b>: podium, fastest lap, the full classification and a <b>Race Progression</b> chart you can drag or play lap by lap; <b>Download image</b> renders a shareable race card PNG in the browser. <b>Stats</b>: click any column to sort." },
        { h: "Colour language",
          p: "One signal colour marks anything active or leading (the current tab, the points leader, the fastest-lap tag): F1's own purple in the Matchday look, cyan in the HUD look. Team colours always identify drivers and constructors; red marks retirements, green marks places gained, amber marks postponed rounds." },
        { h: "Limits",
          p: "The public data has no lap-by-lap positions, so the Race Progression chart is an honest <b>grid → finish (approx)</b> curve built from each driver's real grid, finish and laps completed, not live timing; it switches to real lap data only when a timing-enabled fetch provides it. Laps led likewise needs live timing and is hidden otherwise. Replay videos exist only for races the video workflow has rendered, and the fastf1 pre-season calendar can differ from f1db's live one by a round or two." }
      ]
    },
    he: {
      title: "F1 Visualized",
      intro: "לוח מחוונים לעונות הפורמולה 1 בשנים 2022–2026, ולצדו Pipeline בפייתון שהופך את נתוני התזמון של מרוץ, הקפה אחר הקפה, לסרטוני שחזור בסגנון שידור טלוויזיה. הכול נשען על נתונים ציבוריים בלי מפתח API, והאתר סטטי: GitHub Actions בונה ומפרסם אותו מחדש באופן אוטומטי.",
      sections: [
        { h: "מה זה",
          p: "בריפוזיטורי אחד יש שני חלקים. <b>לוח המחוונים</b> (העמוד הזה) מכסה חמש עונות בחמש תצוגות: סקירה, טבלאות, לוח מרוצים, תוצאות וסטטיסטיקה, עם בורר עונה בראש העמוד. <b>ה-Pipeline לווידאו</b> אוסף את נתוני הגרנד פרי האחרון שהסתיים ומפיק שני סרטוני MP4 ברזולוציה 1280×720: \"מרוץ\" שבו כל מכונית מחליקה בין נתיבי המיקום הקפה אחר הקפה, וגרף מיקומים קלאסי לפי הקפה (bump chart). אפשר גם לחבר את שניהם זה לצד זה לסרטון אחד מסונכרן." },
        { h: "מקורות הנתונים והיקפם",
          p: "הסקריפט <code>fetch_season.py</code> בונה קובץ JSON לכל עונה משני מקורות ציבוריים: <b>לוח המרוצים</b> מ-<code>fastf1.get_event_schedule</code>, ו<b>תוצאות, טבלאות, עמדות זינוק, הקפות מהירות ועצירות פיט</b> ממאגר הקוד הפתוח <b>f1db</b> (קובצי ה-YAML שלו ב-GitHub). בתמונת המצב השמורה יש 114 סבבים מתוכננים בין 2022 ל-2026 וכ-2,000 שורות תוצאה מסווגות. מרוץ מתוכנן שעוד אין לו תוצאה מוצג כ-<b>TBC</b> (טרם נקבע), ולא ממציאים לו נתונים." },
        { h: "ה-Pipeline והאוטומציה",
          p: "תהליך GitHub Actions מושך מחדש את עונות 2025 ו-2026 בכל שלישי ושישי ב-06:00 UTC (אחרי סופי שבוע של מרוצים), בכל push ולפי דרישה, ומפרסם את תיקיית <code>web/</code> ל-GitHub Pages. אם מקור הנתונים לא זמין, מתפרסמים הנתונים השמורים, כך שהאתר תמיד עולה. תהליך שני, לפי דרישה, מריץ את ה-Pipeline לווידאו: <code>scraper.py</code> מאתר את המרוץ האחרון שנתוני התזמון שלו פורסמו, מחלץ לכל נהג בכל הקפה מיקום, תרכובת צמיגים, עצירות פיט והקפות תחת Virtual Safety Car, ושני מנועי matplotlib מרנדרים את הסרטונים בעזרת ffmpeg." },
        { h: "השיטות שמאחורי המספרים",
          p: "<b>הסטטיסטיקה העונתית</b> מסכמת את כל הסבבים שהסתיימו: ניצחונות, פודיומים, פול פוזישן, זינוקים, מיקום זינוק וסיום ממוצע, מקומות שהורוויחו מהזינוק עד הדגל, סיומים בנקודות, פרישות ופרסי Driver of the Day. <b>Stop (s)</b> הוא אומדן: f1db רושם רק את הזמן המלא בנתיב הפיט, שנקבע בעיקר לפי אורך הנתיב בכל מסלול, ולכן העצירה המהירה במרוץ נחשבת לזמן המעבר המשותף ומופחתת (העצירה המהירה ביותר מקבלת רצפה של 2.0 שניות), ומוצג החציון. <b>צבעי קבוצות</b> קרובים מדי (רד בול, רייסינג בולס וויליאמס כחולות כולן) נבדקים בכל עונה במבחן הבדל צבע CIE76 ΔE, והצבע של הקבוצה הנמוכה בטבלה מוזז מעט." },
        { h: "איך לקרוא את התצוגות",
          p: "<b>סקירה</b>: שני מובילי האליפות עם פס שמראה את חלקם מסך הנקודות של המוביל והשני, ספירה לאחור למרוץ הבא, הפודיום האחרון וחמשת הראשונים. <b>טבלאות</b>: הדירוג המלא עם פסי נקודות בצבעי הקבוצות. <b>לוח מרוצים</b>: כל סבב והסטטוס שלו; לחיצה על מרוץ שהסתיים פותחת אותו. <b>תוצאות</b>: פודיום, הקפה מהירה, הדירוג המלא וגרף <b>התקדמות המרוץ</b> שאפשר לגרור או להפעיל הקפה אחר הקפה; <b>הורדת תמונה</b> מפיקה בדפדפן כרטיס מרוץ PNG לשיתוף. <b>סטטיסטיקה</b>: לחיצה על עמודה ממיינת לפיה." },
        { h: "שפת הצבעים",
          p: "צבע אות אחד מסמן כל דבר פעיל או מוביל (הלשונית הנוכחית, מוביל הנקודות, תג ההקפה המהירה): הסגול של הפורמולה 1 עצמה במראה Matchday, וציאן במראה HUD. צבעי הקבוצות תמיד מזהים נהגים וקבוצות; אדום מסמן פרישה, ירוק מקומות שהורוויחו, וענבר סבבים שנדחו." },
        { h: "מגבלות",
          p: "בנתונים הציבוריים אין מיקומים לפי הקפה, ולכן גרף התקדמות המרוץ הוא עקומה מוצהרת של <b>זינוק → סיום (בקירוב)</b>, הבנויה מעמדת הזינוק, מקום הסיום ומספר ההקפות האמיתיים של כל נהג, ולא תזמון חי; הוא עובר לנתוני הקפות אמיתיים רק כשמשיכה עם נתוני תזמון מספקת אותם. גם הקפות בהובלה דורשות תזמון חי ומוסתרות בלעדיו. סרטוני שחזור קיימים רק למרוצים שתהליך הווידאו רינדר, ולוח המרוצים של fastf1 לפני העונה יכול להיות שונה בסבב או שניים מהלוח החי של f1db." }
      ]
    }
  };

  var he = {
    // top bar, tabs, labels
    "Overview": "סקירה",
    "Standings": "טבלאות",
    "Calendar": "לוח מרוצים",
    "Results": "תוצאות",
    "Stats": "סטטיסטיקה",
    "Season": "עונה",
    "Sections": "אזורים",
    // overview
    "Drivers' Championship Leader": "מוביל אליפות הנהגים",
    "Constructors' Championship Leader": "מובילת אליפות הקבוצות",
    "points": "נקודות",
    "Next Race": "המרוץ הבא",
    "days to go": "ימים למרוץ",
    "day to go": "יום למרוץ",
    "Season complete": "העונה הסתיימה",
    "Last Race": "המרוץ האחרון",
    "No races completed yet.": "עוד לא הסתיים אף מרוץ.",
    "Top 5 — Drivers": "5 הראשונים — נהגים",
    "Top 5 — Constructors": "5 הראשונות — קבוצות",
    // standings
    "Drivers' Championship": "אליפות הנהגים",
    "Constructors' Championship": "אליפות הקבוצות",
    // calendar
    "Race Calendar": "לוח המרוצים",
    "Completed": "הסתיים",
    "Postponed": "נדחה",
    "Next Up": "הבא בתור",
    "TBC": "טרם נקבע",
    "Upcoming": "בקרוב",
    "Not held": "לא התקיים",
    // results
    "Race Results": "תוצאות המרוץ",
    "Race": "מרוץ",
    "Download image": "הורדת תמונה",
    "Rendering…": "מרנדר…",
    "No completed races": "אין מרוצים שהסתיימו",
    "No completed races in this season yet.": "עוד לא הסתיימו מרוצים בעונה הזו.",
    "No results available.": "אין תוצאות זמינות.",
    "⏱ Fastest Lap": "⏱ הקפה מהירה",
    "⏱ Fastest lap —": "⏱ הקפה מהירה —",
    "Race Progression": "התקדמות המרוץ",
    "grid → finish (approx) · drag or play to scrub": "זינוק → סיום (בקירוב) · גררו או הפעילו כדי לדפדף",
    "lap-by-lap · drag or play to scrub": "הקפה אחר הקפה · גררו או הפעילו כדי לדפדף",
    "Play": "הפעלה",
    "Pause": "השהיה",
    "Lap": "הקפה",
    "Pick lap": "בחירת הקפה",
    "Race Replay": "שחזור המרוץ",
    "rendered animation": "אנימציה מרונדרת",
    "sample render": "רינדור לדוגמה",
    "Pos": "מקום",
    "Driver": "נהג",
    "Team": "קבוצה",
    "Grid": "זינוק",
    "Laps / Status": "הקפות / סטטוס",
    "Pts": "נק׳",
    // stats
    "Season Stats": "סטטיסטיקה עונתית",
    "Points": "נקודות",
    "Wins": "ניצחונות",
    "Podiums": "פודיומים",
    "Poles": "פול פוזישן",
    "Starts": "זינוקים",
    "Avg Finish": "סיום ממוצע",
    "Avg Grid": "זינוק ממוצע",
    "Places +/−": "מקומות +/−",
    "Avg Stops": "עצירות בממוצע",
    "Stop (s)": "עצירה (שנ׳)",
    "Pts Fin": "סיומים בנקודות",
    "DNF": "פרישות",
    "DOTD": "נהג היום",
    "Laps Led": "הקפות בהובלה",
    "Every completed round, aggregated. Wins · podiums · poles are Grand Prix figures;": "סיכום של כל הסבבים שהסתיימו. ניצחונות, פודיומים ופול פוזישן הם נתוני הגרנד פרי;",
    "is the championship total.": "הוא סך הנקודות באליפות.",
    "Places +/−": "מקומות +/−",
    "is net positions gained from grid to flag (front-runners naturally trend negative).": "הוא מאזן המקומות שהורוויחו מהזינוק עד הדגל (המובילים נוטים באופן טבעי למאזן שלילי).",
    "Stop (s)": "עצירה (שנ׳)",
    "estimates the stationary tyre-change time — the circuit's pit-lane transit is removed from the public data, which records only full pit-lane time. Click any column to sort.": "מעריך את זמן העמידה להחלפת צמיגים: זמן המעבר בנתיב הפיט של המסלול מופחת מהנתונים הציבוריים, שרושמים רק את הזמן המלא בנתיב. לחיצה על עמודה ממיינת לפיה.",
    "Laps-led needs lap-by-lap timing — not in the public dataset — so it shows only after a timing-enabled fetch.": "הקפות בהובלה דורשות תזמון הקפה אחר הקפה, שאינו בנתונים הציבוריים, ולכן הן מוצגות רק אחרי משיכה עם נתוני תזמון.",
    "Championship points (includes sprints)": "נקודות אליפות (כולל ספרינטים)",
    "Grand Prix wins": "ניצחונות בגרנד פרי",
    "Top-3 finishes": "סיומים בשלושת הראשונים",
    "Qualifying P1": "מקום ראשון במקצה הדירוג",
    "Grand Prix starts": "זינוקים בגרנד פרי",
    "Mean finish position — lower is better": "מקום סיום ממוצע — נמוך יותר עדיף",
    "Mean start position — lower is better": "מקום זינוק ממוצע — נמוך יותר עדיף",
    "Net positions gained, grid → flag (front-runners trend negative)": "מאזן מקומות מהזינוק עד הדגל (המובילים נוטים לשלילי)",
    "Average pit stops per race": "ממוצע עצירות פיט למרוץ",
    "Est. stationary tyre-change time — median, with pit-lane transit removed (public data records only full pit-lane time) — lower is better": "אומדן זמן העמידה להחלפת צמיגים — חציון, בניכוי המעבר בנתיב הפיט (הנתונים הציבוריים רושמים רק את הזמן המלא בנתיב) — נמוך יותר עדיף",
    "Points finishes (top 10)": "סיומים בנקודות (עשרת הראשונים)",
    "Did not finish": "לא סיים",
    "Driver of the Day awards": "פרסי נהג היום",
    // footer
    "F1 Visualized · seasons 2022–2026": "F1 Visualized · עונות 2022–2026",
    "Data via f1db + fastf1": "נתונים: f1db + fastf1"
  };

  // Short counted phrases the dashboard builds from numbers.
  var i, j;
  for (i = 0; i <= 30; i++) {
    he[i + " wins"] = i + " ניצחונות";
    he["Round " + i] = "סבב " + i;
    he["All " + i + " rounds finished 🏁"] = "כל " + i + " הסבבים הסתיימו 🏁";
  }
  he["1 win"] = "ניצחון אחד";
  for (i = 0; i <= 30; i++) for (j = 1; j <= 30; j++) {
    he[i + " of " + j + " rounds completed"] = i + " מתוך " + j + " סבבים הסתיימו";
    he[i + " drivers · " + j + " rounds"] = i + " נהגים · " + j + " סבבים";
  }
  // Phrases with a name or date inside ("Lead over RUS:", "Mercedes · 5 wins") are matched by
  // pattern; the name/date part is data and stays as it is.
  var patterns = [
    [/^Lead over (.+):$/, function (m) { return "יתרון על " + m[1] + ":"; }],
    [/^(.+) · (\d+) wins?$/, function (m) { return m[1] + " · " + (m[2] === "1" ? "ניצחון אחד" : m[2] + " ניצחונות"); }],
    [/^Last Race — (.+)$/, function (m) { return "המרוץ האחרון — " + m[1]; }],
    [/^Updated (.+)$/, function (m) { return "עודכן " + m[1]; }]
  ];
  function lookup(k) {
    if (Object.prototype.hasOwnProperty.call(he, k)) return he[k];
    if (typeof k !== "string") return undefined;
    for (var n = 0; n < patterns.length; n++) { var m = patterns[n][0].exec(k); if (m) return patterns[n][1](m); }
    return undefined;
  }
  window.RS_I18N = typeof Proxy === "function" ? new Proxy(he, {
    get: function (t, k) { return lookup(k); },
    getOwnPropertyDescriptor: function (t, k) {
      var v = lookup(k);
      return v === undefined ? undefined : { value: v, writable: true, enumerable: true, configurable: true };
    }
  }) : he;
  if (window.RSBrand) window.RSBrand.refresh();
})();
