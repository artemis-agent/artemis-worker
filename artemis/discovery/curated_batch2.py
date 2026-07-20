"""Additional curated tech companies — supplement to curated.py.

Targets: lesser-known but viable startups likely on Greenhouse/Lever/Ashby.
Goal: bridge the gap to 1500+ verified companies.
"""

CURATED_BATCH_2 = [
    # ── Vertical SaaS ────────────────────────────────────────────────────
    "Toast", "Olo", "Tock", "OpenTable", "Yelp",
    "ServiceTitan", "Procore", "Buildertrend", "PlanGrid", "Autodesk",
    "Bluebeam", "Field Nation", "Workiz", "Jobber", "ServiceMax",
    "Veeva Systems", "IQVIA", "Definitive Healthcare", "InVivo Health",
    "Komodo Health", "Trilliant Health", "Aledade", "Privia Health",
    "Truepill", "Capsule", "PillPack", "Alto Pharmacy",
    "Cedar", "Olive", "Notable Health", "Suki AI", "Abridge",
    "Iodine Software", "Memora Health", "Hint Health",

    # ── Govtech / civic ──────────────────────────────────────────────────
    "Palantir", "Anduril", "Shield AI", "Skydio",
    "GovCIO", "MITRE", "Tyler Technologies", "Granicus", "Bidgely",
    "Mark43", "Axon", "Flock Safety", "OpenGov", "Civis Analytics",
    "Civitech", "Bonterra", "Resilient Coders",

    # ── Education tech ───────────────────────────────────────────────────
    "Khan Academy", "Khan Lab School", "EdReports", "Renaissance Learning",
    "Cengage", "McGraw Hill", "Pearson", "Discovery Education",
    "DreamBox", "IXL Learning", "Curriculum Associates", "Newsela",
    "Schoology", "Canvas", "Blackboard", "PowerSchool", "Skyward",
    "Skooler", "GoGuardian", "Securly", "Lightspeed Systems",
    "Brightwheel", "ParentSquare", "ClassDojo", "Class Tech",
    "OutSchool", "Varsity Tutors", "Wyzant", "TakeLessons",
    "Brilliant", "Codecademy", "Treehouse", "DataCamp", "Educative",
    "Frontend Masters", "Pluralsight", "LinkedIn Learning",

    # ── Consumer apps ────────────────────────────────────────────────────
    "Bumble", "Hinge", "Match", "OkCupid", "Plenty of Fish",
    "Tinder", "Coffee Meets Bagel", "League", "Raya",
    "Strava", "Nike Run Club", "MapMyRun", "Runkeeper",
    "Whoop", "Oura", "Fitbit", "Garmin Connect", "Polar Flow",
    "Calm", "Headspace", "Insight Timer", "Aura", "Balance",
    "MyFitnessPal", "Cronometer", "Noom", "WW",
    "BetterMe", "Future", "Tonal", "Mirror", "Hydrow",
    "Peloton", "iFit", "Echelon", "NordicTrack", "Bowflex",
    "Plant Nanny", "Habitica", "Sleep Cycle", "Pillow",

    # ── Music & audio ────────────────────────────────────────────────────
    "Spotify", "SoundCloud", "Bandcamp", "Pandora", "Tidal",
    "Apple Music", "YouTube Music", "Amazon Music", "Audible", "Storytel",
    "Wondery", "Gimlet Media", "Pushkin Industries", "Acast", "Anchor",
    "Castbox", "Pocket Casts", "Overcast", "Stitcher",
    "Splice", "Output", "iZotope", "Native Instruments", "Ableton",
    "BandLab", "Soundtrap", "Endel", "Mubert",

    # ── Productivity, communication ──────────────────────────────────────
    "Slack", "Discord", "Mattermost", "Element", "Wire",
    "Microsoft Teams", "Webex", "BlueJeans", "GoTo", "Whereby",
    "Around", "Tandem", "Spatial", "Gather", "Spot.work",
    "Loom", "Tella", "Riverside", "Squadcast", "Buzzsprout",
    "Otter", "Fireflies", "Sembly", "tl;dv", "Read AI",
    "Granola", "Bee AI", "Plaud", "Limitless",

    # ── Sales & marketing tech ──────────────────────────────────────────
    "Salesforce", "HubSpot", "Pipedrive", "Close", "Freshworks",
    "Zoho", "Insightly", "Copper", "Salesflare", "Vtiger",
    "Marketo", "Pardot", "ActiveCampaign", "Mailchimp", "Klaviyo",
    "Drip", "Constant Contact", "GetResponse", "AWeber", "Sendinblue",
    "Mailgun", "SendGrid", "Postmark", "Mandrill", "Brevo",
    "Outreach", "Salesloft", "Mixmax", "Yesware", "Reply.io",
    "Apollo", "ZoomInfo", "Cognism", "Lusha", "RocketReach",
    "Clearbit", "Crunchbase Enterprise", "Owler", "DiscoverOrg",
    "Gong", "Chorus", "Salesken", "ExecVision", "Refract",
    "Drift", "Intercom", "Crisp", "Tidio", "Tawk",
    "Userlist", "Customerly", "Vero", "Hightouch", "Census",

    # ── Fintech (deeper) ─────────────────────────────────────────────────
    "Tipalti", "Stampli", "Airbase", "Divvy", "BILL",
    "Yardi", "AppFolio", "RealPage", "Entrata", "Buildium",
    "Carta", "Pulley", "Vouch", "Pave", "Comprehensive",
    "AngelList", "Republic", "Wefunder", "StartEngine", "SeedInvest",
    "iCapital", "CAIS", "Yieldstreet", "Masterworks", "Rally",
    "Mighty Networks", "Circle", "Discourse", "Vanilla Forums",
    "Wise", "Remitly", "WorldRemit", "Xoom", "Zelle",
    "Cash App", "Venmo", "Apple Pay", "Google Pay", "PayPal",
    "Bolt", "Fast", "Shop Pay", "Klarna", "Afterpay",
    "Affirm", "Sezzle", "Zip", "Splitit", "Quadpay",
    "Riskified", "Forter", "Signifyd", "Sift", "Kount",
    "Persona", "Onfido", "Jumio", "Veriff", "Mitek",
    "Plaid", "Yodlee", "MX Technologies", "Tink", "TrueLayer",
    "Modern Treasury", "Routable", "Fragment", "Increase", "Treasury Prime",
    "Synapse", "Galileo", "Marqeta", "Lithic", "Highnote",

    # ── B2B procurement & ops ────────────────────────────────────────────
    "Coupa", "Ariba", "Procurify", "Vendr", "Tropic",
    "Sastrify", "Spendflo", "Cledara", "Zylo", "Productiv",
    "Stripe Atlas", "Firstbase", "Doola", "Pilot Bookkeeping", "Bench",
    "Cube Software", "Causal", "Mosaic", "Vena", "OnPlan",
    "Anaplan", "Workday Adaptive", "Pigment", "Datarails", "Spotlightr",

    # ── Customer experience ──────────────────────────────────────────────
    "Zendesk", "Freshdesk", "Help Scout", "Front", "Crisp",
    "LiveAgent", "Kustomer", "Re:amaze", "Olark", "LiveChat",
    "Tidio", "Drift", "Intercom", "HubSpot Service", "Salesforce Service",
    "Talkdesk", "Five9", "NICE", "Genesys", "Aircall",
    "JustCall", "Toky", "Kixie", "CallRail", "CallTrackingMetrics",
    "Survicate", "Typeform", "Jotform", "SurveyMonkey", "Qualtrics",
    "Hotjar", "FullStory", "Mouseflow", "Lucky Orange",
    "UserTesting", "Maze", "Hotjar", "Smartlook", "PostHog",

    # ── DevOps / SRE ─────────────────────────────────────────────────────
    "PagerDuty", "Opsgenie", "VictorOps", "FireHydrant", "Rootly",
    "incident.io", "Squadcast", "Blameless", "Jeli", "Transposit",
    "Datadog", "New Relic", "Dynatrace", "Splunk", "AppDynamics",
    "Honeycomb", "Lightstep", "Aspecto", "Cribl", "Edge Delta",
    "Sentry", "Rollbar", "Bugsnag", "Raygun", "Airbrake",
    "LogRocket", "Highlight", "Sprout", "Posthog",
    "CircleCI", "GitLab CI", "GitHub Actions", "Travis CI", "Buildkite",
    "Drone CI", "Jenkins", "TeamCity", "Bamboo", "Codefresh",
    "Argo CD", "FluxCD", "Codacy", "SonarSource", "DeepCode",
    "Atlantis", "Spacelift", "env0", "Pulumi", "Terraform Cloud",
    "Vagrant", "Packer", "Vault", "Consul", "Nomad",
    "Crossplane", "Backstage", "OpsLevel", "Cortex", "Rely",
    "Humanitec", "Mia Platform", "Squareflood",

    # ── Data eng / analytics ─────────────────────────────────────────────
    "Snowflake", "Databricks", "Starburst", "Dremio", "Imply",
    "DataRobot", "H2O.ai", "Dataiku", "Alteryx", "RapidMiner",
    "Domino Data Lab", "Iguazio", "Cnvrg.io", "ClearML", "Comet",
    "Weights & Biases", "Neptune.ai", "MLflow", "Determined AI", "Anyscale",
    "Modal", "Outerbounds", "Domino Data Lab", "Valohai", "Polyaxon",
    "Hex", "Mode", "Sigma", "Hightouch", "Census",
    "Looker", "Tableau", "Power BI", "Qlik", "ThoughtSpot",
    "Metabase", "Superset", "Redash", "Lightdash", "Holistics",
    "Cube", "AtScale", "GoodData", "Domo", "Yellowfin",
    "Preset", "Streamlit", "Plotly", "Dash", "Bokeh",

    # ── Misc unicorns & well-known SaaS ──────────────────────────────────
    "Canva", "Miro", "Mural", "Figma", "Whimsical",
    "Notion", "Coda", "Airtable", "ClickUp", "Monday.com",
    "Asana", "Wrike", "Smartsheet", "Trello", "Basecamp",
    "Linear", "Height", "Shortcut", "Jira", "GitLab",
    "Loom", "Vidyard", "BombBomb", "Wistia", "Vimeo",
    "Webflow", "Squarespace", "Wix", "Shopify", "BigCommerce",
    "Mailchimp", "ConvertKit", "Substack", "Beehiiv", "Ghost",
    "Mighty Networks", "Circle", "Discourse", "Skool",
    "Beehive Software", "Common Room", "Orbit", "Bevy",
    "Linktree", "Beacons", "Stan Store", "Komi",
    "Hopin", "Bizzabo", "Run The World", "Welcome", "vFairs",
    "Goldcast", "Brandlive", "Cvent", "Bizzabo",
    "Calendly", "SavvyCal", "Cal.com", "YouCanBookMe", "Acuity Scheduling",
    "Doodle", "When2meet", "Setmore", "10to8",

    # ── Specialty fintech ────────────────────────────────────────────────
    "Robinhood", "Webull", "Public", "M1 Finance", "SoFi",
    "Acorns", "Stash", "Betterment", "Wealthfront", "Personal Capital",
    "Empower", "Mint", "YNAB", "Rocket Money", "Truebill",
    "Copper", "Greenlight", "GoHenry", "FamZoo", "Step",
    "Current", "Chime", "Varo", "Aspiration", "Ally",
    "Marcus", "American Express", "Capital One", "Discover", "Synchrony",
    "Affirm", "Klarna", "Sezzle", "Afterpay", "Quadpay",
    "Stripe Issuing", "Marqeta", "Lithic", "Highnote", "Synapse",
    "Galileo", "Bond", "Treasury Prime", "Unit", "Increase",

    # ── Hot enterprise SaaS ──────────────────────────────────────────────
    "Atlassian", "Asana", "Monday.com", "Smartsheet", "Wrike",
    "ClickUp", "Notion", "Coda", "Airtable", "Glide",
    "Zapier", "Make", "n8n", "Tray.io", "Workato",
    "MuleSoft", "Boomi", "SnapLogic", "Celigo", "Jitterbit",
    "Twilio", "Plivo", "MessageBird", "Sinch", "Bandwidth",
    "Vonage", "RingCentral", "8x8", "Dialpad", "Zoom",
    "Cisco WebEx", "Microsoft Teams", "Google Meet", "Whereby",
    "Vimeo", "Vidyard", "Wistia", "Loom", "Brightcove",
    "Kaltura", "Panopto", "Sonix", "Otter", "Rev",

    # ── Hot agency / freelance ───────────────────────────────────────────
    "Toptal", "Upwork", "Fiverr", "Freelancer", "PeoplePerHour",
    "99designs", "Crowdspring", "DesignCrowd", "Tongal",
    "Catalant", "Business Talent Group", "MBO Partners", "GLG",
    "Andela", "Turing", "Arc.dev", "Lemon.io", "Toptal",
    "Codementor", "Codility", "HackerRank", "LeetCode",

    # ── Bio & biotech ────────────────────────────────────────────────────
    "23andMe", "Ancestry", "MyHeritage", "Helix", "Color Genomics",
    "Veritas Genetics", "Invitae", "Natera", "Guardant Health", "Foundation Medicine",
    "Recursion", "Insitro", "Tempus Labs", "Tempus AI", "Verge Genomics",
    "Atomic AI", "AbCellera", "Generate Biomedicines", "Asimov", "Synthego",
    "Twist Bioscience", "Inscripta", "Mammoth Biosciences", "Caribou Biosciences",
    "Editas Medicine", "Intellia Therapeutics", "Beam Therapeutics", "CRISPR Therapeutics",
    "Sana Biotechnology", "Verve Therapeutics", "Prime Medicine",
    "Moderna", "BioNTech", "CureVac", "Translate Bio", "Arcturus Therapeutics",
    "Pfizer", "Eli Lilly", "Merck", "Johnson & Johnson", "AbbVie",
    "Sanofi", "GSK", "AstraZeneca", "Bristol Myers Squibb", "Novartis",

    # ── Climate tech ─────────────────────────────────────────────────────
    "Sublime Systems", "Solidia Technologies", "CarbonCure",
    "Charm Industrial", "Running Tide", "Captura",
    "Lilac Solutions", "Mangrove Lithium", "Sila Nanotechnologies",
    "QuantumScape", "Solid Power", "Factorial Energy", "ProLogium",
    "Group14 Technologies", "Sila Nanotechnologies",
    "Heliogen", "Brimstone", "Sublime Systems", "Boston Metal",
    "Electric Hydrogen", "Verdagy", "Ohmium International",
    "Synhelion", "Heliogen", "Antora Energy", "Rondo Energy",
    "Modern Hydrogen", "Aurora Hydrogen", "Monolith",
    "Pivotal Commware", "Ookla", "Speedtest",

    # ── Real estate proptech ─────────────────────────────────────────────
    "Compass", "Opendoor", "Offerpad", "Zillow", "Redfin",
    "Realtor.com", "Trulia", "Homesnap", "HomeLight", "OJO Labs",
    "Side", "Real Brokerage", "eXp Realty", "Keller Williams", "RE/MAX",
    "Cherre", "Reonomy", "CompStak", "VTS", "Building Engines",
    "RealPage", "Yardi", "AppFolio", "Buildium", "Entrata",
    "Latch", "Smartrent", "Brivo", "August Home", "Ring",
    "Cove Smart", "Wyze", "SimpliSafe", "ADT", "Vivint",
    "EquipmentShare", "Pacaso", "Sundae",

    # ── Aerospace & space tech ───────────────────────────────────────────
    "SpaceX", "Blue Origin", "Rocket Lab", "Astra", "Relativity Space",
    "Firefly Aerospace", "ABL Space Systems", "Astranis",
    "Loft Orbital", "Spire Global", "Planet Labs", "Maxar Technologies",
    "BlackSky", "Capella Space", "ICEYE", "Umbra",
    "Boom Supersonic", "Hermeus", "Aerion Supersonic", "Reaction Engines",
    "Joby Aviation", "Wisk Aero", "Archer Aviation", "Lilium", "EHang",
    "Volocopter", "BETA Technologies", "Eve Air Mobility",
    "Skydio", "Saildrone", "Liquid Robotics", "Saronic", "ANYbotics",
    "Boston Dynamics", "ANYbotics", "Agility Robotics", "Sanctuary AI",
    "1X Technologies", "Apptronik", "Figure", "Tesla Optimus",
    "Diligent Robotics", "Veo Robotics", "Path Robotics", "Bright Machines",
]
