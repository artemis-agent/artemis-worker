"""Curated batch 3 — extra coverage to reach 1500+ companies.

Focus areas:
- Lever-using mid-stage startups (we're underrepresented in Lever)
- Recent YC alumni (W21-W25 batches) with known traction
- International scaleups
- Specialty B2B SaaS niches
- Series B/C/D companies
"""

CURATED_BATCH_3 = [
    # ── Recent YC alumni (W21-W25 with traction) ────────────────────────
    "Together.xyz", "Modal Labs", "Pinecone", "LangChain", "LlamaIndex",
    "Anyscale", "Determined AI", "Weights and Biases", "Comet",
    "Datafold", "dbt Labs", "Fivetran", "Hightouch", "Airbyte", "Meltano",
    "Prefect", "Dagster", "Materialize", "ClickHouse",
    "ContextualAI", "Mintlify", "Cursor", "Continue", "Replit",
    "Anysphere", "Codeium", "Codium AI", "Sourcegraph", "Tabnine",
    "Magic AI", "Aider", "Phind", "Bito",
    "Pika Labs", "Luma AI", "Synthesia", "Captions", "Descript",
    "ElevenLabs", "Suno", "Krea AI", "Tome", "Gamma",
    "Riverside", "Otter AI", "Fireflies AI", "Granola", "Read AI",
    "Fathom", "Sembly", "Sembly AI", "Speak", "Babbel",
    "Notta", "Tactiq", "Bee AI", "Plaud", "Limitless",

    # ── Lever customer staples (often missed by other lists) ─────────────
    "Mixpanel", "Amplitude", "Heap", "Segment", "RudderStack",
    "Customer.io", "ConvertKit", "Iterable", "Braze", "Klaviyo",
    "OneSignal", "MoEngage", "Attentive", "Sailthru", "Bloomreach",
    "Yotpo", "Recharge", "Bold Commerce", "Postscript", "Octane AI",
    "Gorgias", "Re:amaze", "Tidio", "Crisp", "Helpshift",
    "Drift", "Intercom", "Front", "HelpScout", "Kustomer",
    "Ada Support", "Forethought", "Cresta", "Replicant",
    "Aircall", "Dialpad", "RingCentral", "Vonage", "Plivo",
    "MessageBird", "Sinch", "Bandwidth", "Twilio", "Plivo",
    "Smartcar", "Tile", "Eero", "Wyze",
    "Ring", "Nest", "Vivint", "ADT", "SimpliSafe",

    # ── Hot Series B/C/D startups in 2024-2025 ──────────────────────────
    "Hippo", "Lemonade", "Root Insurance", "Next Insurance", "Pie Insurance",
    "Embroker", "Newfront", "Coalition", "At-Bay", "Cowbell Cyber",
    "Resilience", "Boost Insurance", "Branch Insurance", "Bolt Insurance",
    "Sentry", "Honeycomb", "LaunchDarkly", "Split", "Optimizely",
    "Unleash", "Statsig", "Featurevisor", "GrowthBook",
    "Vercel", "Netlify", "Cloudflare Pages", "Render", "Railway",
    "Fly.io", "Heroku", "Northflank", "Koyeb",
    "Webflow", "Framer", "Wix Studio", "Bubble", "Glide",
    "Softr", "Adalo", "OutSystems", "Mendix", "Microsoft PowerApps",
    "Retool", "Hex Technologies", "Streamlit", "Plotly",
    "DataRobot", "Dataiku", "H2O.ai", "Alteryx", "Iguazio",

    # ── Cloud, infra, devops ─────────────────────────────────────────────
    "Crusoe Energy", "Lambda Labs", "Vast AI", "RunPod",
    "Modal", "Outerbounds", "Banana", "Inferless",
    "BentoML", "Seldon", "ClearML", "Cnvrg.io",
    "Neptune.ai", "MLflow", "Weights and Biases", "Comet",
    "Snorkel AI", "Labelbox", "Scale AI", "Surge AI", "Toloka",
    "DataLoop", "V7", "Roboflow", "Encord", "Hasty",
    "Voxel51", "Lightly", "Aquarium", "Galileo", "Arize",
    "WhyLabs", "Fiddler", "TruEra", "Robust Intelligence",
    "Verta AI", "Domino Data Lab", "DataRobot", "Mathpresso",
    "Anyscale", "Determined AI", "Ray", "Modal Labs",

    # ── Recent unicorns / fast-growing companies (late 2024-2025) ───────
    "Synthesia", "Adept", "Inflection AI", "Character AI", "Cohere",
    "Mistral AI", "Hugging Face", "Anthropic", "OpenAI", "Perplexity",
    "Magic.dev", "Codeium", "Cognition AI", "Tessl",
    "Glean", "Harvey", "Klarity", "Eve", "Spellbook",
    "Casetext", "Lexion", "DraftWise", "Ironclad", "Robin AI",
    "Hebbia", "Vespper", "Vespa", "Pinecone", "Weaviate",
    "Chroma", "Qdrant", "Milvus", "LanceDB", "Zilliz",
    "MosaicML", "Octo AI", "Together AI", "Anyscale", "Modal",
    "Lambda Labs", "CoreWeave", "FluidStack", "Hyperstack",

    # ── Climate / sustainability ────────────────────────────────────────
    "Watershed", "Persefoni", "Sweep", "Plan A", "Greenly",
    "Pachama", "Patch", "Climeworks", "Carbon Clean", "Heirloom",
    "Crusoe Energy", "Form Energy", "ESS Tech", "Sunrun", "Sunnova",
    "EnergyHub", "Span", "Lunar Energy", "Octopus Energy", "David Energy",
    "Energy Aspects", "WeaveGrid", "EnerKnol", "Camus Energy",
    "Singularity Energy", "Carbon Direct", "Carbon Limit",
    "Climate Engine", "Climate AI",

    # ── DevOps / observability ──────────────────────────────────────────
    "Cribl", "Edge Delta", "Lightstep", "Honeycomb", "OpsRamp",
    "Datadog", "New Relic", "Splunk", "Sumo Logic", "Logz.io",
    "Coralogix", "Logtail", "Better Stack", "Mezmo", "ChaosSearch",
    "Falcon LogScale", "Humio", "Loki", "Grafana Labs", "InfluxData",
    "Timescale", "Prometheus", "VictoriaMetrics", "Cortex Labs",
    "PagerDuty", "Opsgenie", "VictorOps", "Squadcast", "incident.io",
    "FireHydrant", "Rootly", "Blameless", "Jeli", "Transposit",
    "Statuspage", "Statusgator", "Pingdom", "UptimeRobot", "StatusCake",
    "Better Uptime", "Cronitor", "Healthchecks", "Dead Man's Snitch",

    # ── Security ─────────────────────────────────────────────────────────
    "Wiz", "Lacework", "Orca Security", "Aqua Security", "Sysdig",
    "Snyk", "Veracode", "Checkmarx", "Black Duck", "Mend",
    "GitGuardian", "Vanta", "Drata", "Secureframe", "Tugboat Logic",
    "Hyperproof", "Audit Board", "AuditBoard", "OneTrust", "TrustArc",
    "Thoropass", "Sprinto", "Scrut", "Anecdotes", "Trustero",
    "Material Security", "Abnormal Security", "Tessian", "Sublime Security",
    "Hoxhunt", "KnowBe4", "CybeReady", "Living Security",
    "Cybereason", "SentinelOne", "CrowdStrike", "Palo Alto Networks",
    "Zscaler", "Cato Networks", "Netskope", "iboss", "Forcepoint",
    "Cloudflare Zero Trust", "Tailscale", "Twingate", "Banyan Security",
    "Perimeter 81", "Zscaler", "Cloudflare", "Cisco",

    # ── Sales & marketing tech ──────────────────────────────────────────
    "Apollo.io", "ZoomInfo", "Cognism", "Lusha", "RocketReach",
    "Clearbit", "Leadfeeder", "Demandbase", "6sense", "Bombora",
    "TechTarget", "Triblio", "Madison Logic", "Foundry",
    "Gong", "Chorus.ai", "ExecVision", "Refract", "Salesken",
    "Outreach", "Salesloft", "Apollo", "Mixmax", "Reply.io",
    "Yesware", "Mailshake", "Lemlist", "Smartlead", "Instantly",
    "Customer.io", "Iterable", "Braze", "Klaviyo", "Mailchimp",
    "HubSpot", "ActiveCampaign", "ConvertKit", "Drip", "Sendinblue",
    "Brevo", "Mailgun", "SendGrid", "Postmark", "Resend",
    "Loops", "Knock", "Courier", "MagicBell", "Beamer",

    # ── Vertical SaaS ────────────────────────────────────────────────────
    "ServiceTitan", "Procore", "Buildertrend", "PlanGrid", "Autodesk Construction",
    "Bluebeam", "Field Nation", "Workiz", "Jobber", "Housecall Pro",
    "ServiceMax", "PTC ThingWorx", "Augury", "Uptake", "Predii",
    "Veeva Systems", "IQVIA", "Definitive Healthcare", "Komodo Health",
    "Datavant", "Health Gorilla", "Particle Health", "Redox", "Innovaccer",
    "Truepill", "Capsule", "PillPack", "Alto Pharmacy", "Honeybee Health",
    "Cedar", "Olive", "Notable Health", "Suki AI", "Abridge",
    "Iodine Software", "Memora Health", "Hint Health", "Wellth", "Vida Health",
    "Hinge Health", "Sword Health", "Omada Health", "Livongo", "Teladoc",
    "Doctor on Demand", "MDLive", "Amwell", "Ro", "Hims",
    "Lemonaid", "Plushcare", "Sesame Care", "Forward", "One Medical",
    "Carbon Health", "Crossover Health", "Devoted Health", "Oscar Health",

    # ── Logistics & supply chain ────────────────────────────────────────
    "Flexport", "Forto", "Sennder", "Loadsmart", "Stord",
    "ShipBob", "Flowspace", "Deliverr", "ShipMonk", "ShipStation",
    "Locus Robotics", "Onfleet", "Bringg", "DispatchTrack", "Routific",
    "Samsara", "KeepTruckin", "Motive", "Geotab", "Verizon Connect",
    "Convoy", "Uber Freight", "Echo Global", "Project44", "FourKites",
    "FreightWaves", "TransImpact", "Convey", "Shippo", "EasyPost",
    "Easyship", "ShippingEasy", "ShippyPro", "Sendcloud", "Packlink",

    # ── Fintech (deeper) ─────────────────────────────────────────────────
    "Tipalti", "Stampli", "Airbase", "Divvy", "BILL.com",
    "BILL", "Expensify", "Ramp", "Brex", "Mercury",
    "Pulley", "Carta", "Vouch", "Pave", "Comprehensive",
    "Justworks", "Gusto", "Rippling", "Deel", "Remote",
    "Velocity Global", "Globalization Partners", "Multiplier", "Oyster",
    "Lattice", "15Five", "Culture Amp", "Glint", "Officevibe",
    "Greenhouse", "Lever", "Ashby", "Workable", "JazzHR",
    "Gem", "Bullhorn", "Recruitee", "BambooHR", "Personio",
    "Hibob", "Charthop", "Pave", "Sequoia One",
    "Modern Treasury", "Routable", "Fragment", "Increase", "Treasury Prime",
    "Synapse", "Galileo", "Marqeta", "Lithic", "Highnote",
    "Unit", "Bond", "Stripe Issuing", "Synctera",

    # ── Education tech ───────────────────────────────────────────────────
    "Coursera", "Udemy", "Pluralsight", "Skillshare", "MasterClass",
    "Outschool", "GoStudent", "Quizlet", "Duolingo", "Babbel",
    "Lingoda", "italki", "Preply", "Cambly", "Speak",
    "Khan Academy", "ClassDojo", "Remind", "Schoology", "PowerSchool",
    "Newsela", "BetterUp", "Maven", "Section", "On Deck",
    "Brilliant", "Codecademy", "Treehouse", "DataCamp", "Educative",
    "Frontend Masters", "Pluralsight", "LinkedIn Learning", "edX", "FutureLearn",
    "Class Tech", "Top Hat", "Pearson", "McGraw Hill", "Cengage",
    "Renaissance Learning", "DreamBox", "IXL Learning", "Curriculum Associates",

    # ── Real estate / proptech ──────────────────────────────────────────
    "Compass", "Opendoor", "Offerpad", "Zillow", "Redfin",
    "Realtor.com", "Trulia", "HomeLight", "Side", "Real Brokerage",
    "eXp Realty", "Keller Williams", "RE/MAX", "Cherre", "Reonomy",
    "CompStak", "VTS", "Building Engines", "RealPage", "Yardi",
    "AppFolio", "Buildium", "Entrata", "Latch", "Smartrent",
    "Brivo", "August Home", "Ring", "Cove Smart", "Wyze",
    "SimpliSafe", "ADT", "Vivint", "EquipmentShare", "Pacaso", "Sundae",

    # ── Travel & hospitality ────────────────────────────────────────────
    "Airbnb", "VRBO", "Vacasa", "Sonder", "Selina",
    "Soho House", "Marriott", "Hilton", "Hyatt", "Booking Holdings",
    "Expedia Group", "TripActions", "Navan", "Spotnana", "Hopper",
    "Skiplagged", "Google Travel", "Skyscanner", "Kayak", "Roadrunner",
    "Outdoorsy", "RVshare", "Hipcamp", "Wanderlog", "TripIt",

    # ── Food & delivery ─────────────────────────────────────────────────
    "DoorDash", "Uber Eats", "Grubhub", "Postmates", "Caviar",
    "Instacart", "GoPuff", "Gorillas", "Getir", "Flink",
    "Wonder", "Slice", "Toast", "ChowNow", "Square for Restaurants",
    "Olo", "Lunchbox", "Tock", "OpenTable", "Resy",
    "SevenRooms", "Tablein", "Tablecheck", "Sweetgreen", "CAVA",
    "Chipotle", "Shake Shack", "Wingstop", "Domino's Pizza", "Papa John's",

    # ── Marketplaces ─────────────────────────────────────────────────────
    "Etsy", "eBay", "OfferUp", "Mercari", "ThredUp",
    "Poshmark", "Depop", "Vestiaire Collective", "GOAT", "StockX",
    "Fanatics", "Whatnot", "NTWRK", "Curated", "Tradeshift",
    "Stargate", "Procurify", "Vendr", "Tropic", "Faire",
    "Wholesale", "Joor", "NuOrder", "Brandboom", "RangeMe",

    # ── Gaming ──────────────────────────────────────────────────────────
    "Epic Games", "Unity", "Roblox", "Niantic", "Supercell",
    "King", "Zynga", "Playtika", "Scopely", "Jam City",
    "Wildlife Studios", "miHoYo", "NetEase", "Tencent Games", "Riot Games",
    "Activision Blizzard", "Electronic Arts", "Ubisoft", "Take-Two", "Embracer Group",
    "CD Projekt Red", "Mythical Games", "Sky Mavis", "Animoca Brands", "Yuga Labs",
    "Skillz", "DraftKings", "FanDuel", "PrizePicks", "Underdog Fantasy",

    # ── Asia / international ─────────────────────────────────────────────
    "Razorpay", "Cred", "Slice", "Paytm", "PhonePe",
    "Zerodha", "Groww", "Upstox", "INDmoney", "Smallcase",
    "Meesho", "Udaan", "OfBusiness", "Zetwerk", "Moglix",
    "Swiggy", "Zomato", "BigBasket", "Grofers", "Dunzo",
    "OYO", "Treebo", "FabHotels", "MakeMyTrip", "Cleartrip",
    "Goibibo", "ixigo", "Yatra", "EaseMyTrip",
    "Byju's", "Vedantu", "Unacademy", "PhysicsWallah", "Whitehat Jr",
    "Cure.Fit", "Cult.fit", "HealthifyMe", "Pharmeasy", "Practo",
    "1mg", "PharmEasy", "Lybrate", "DocsApp", "Mfine",
    "Grab", "Gojek", "Tokopedia", "Bukalapak", "Traveloka",
    "Carousell", "Shopee", "Lazada", "Sea Group", "Garena",
    "Razer", "Sea Limited", "Tiket.com", "Halodoc", "Alodokter",
    "Klook", "Trip.com", "JD.com", "Pinduoduo", "Alibaba",
    "DiDi", "Meituan", "Bilibili", "Kuaishou", "ByteDance",
    "TikTok", "Pico Interactive", "DJI", "Xpeng",
    "BlaBlaCar", "Doctolib", "Qonto", "Ledger", "Mistral AI",
    "Sendinblue", "Contentsquare", "Mirakl", "Klarna", "iZettle",
    "Truecaller", "Wolt", "Bolt", "Pleo", "Lendable",
    "Monzo", "Revolut", "N26", "Wise", "Atom Bank",
    "Tide", "Curve", "Marshmallow", "Cuvva", "Cazoo",
    "Cazoo", "Onfido", "Tessian", "Darktrace", "Sophos",
    "Snyk", "Improbable", "Graphcore", "ARM Holdings", "Spotify",
    "King", "Klarna", "Truecaller", "iZettle", "Mojang",

    # ── Misc B2B SaaS ────────────────────────────────────────────────────
    "Confluent", "MongoDB", "Snowflake", "Databricks", "Datadog",
    "PagerDuty", "Cloudflare", "Fastly", "Twilio", "Sendbird",
    "GitLab", "GitHub", "HashiCorp", "Couchbase", "Elastic",
    "Redis", "Neo4j", "Aerospike", "DataStax", "Cockroach Labs",
    "Yugabyte", "Timescale", "InfluxData", "Materialize", "Singlestore",
    "Arctic Wolf", "JFrog", "Sonatype", "Cycode", "Snyk",
    "Strapi", "Sanity", "Contentful", "Storyblok", "Hygraph",
    "Supabase", "Firebase", "Appwrite", "Nhost", "PocketBase",
    "Notion", "Coda", "Airtable", "Smartsheet", "Monday.com",
    "ClickUp", "Asana", "Trello", "Linear", "Height",
    "Shortcut", "Jira", "GitLab", "GitHub", "Bitbucket",
    "Slack", "Discord", "Mattermost", "Element", "Wire",
    "Zoom", "Twilio", "Plivo", "MessageBird", "Sinch",
    "Loom", "Vidyard", "BombBomb", "Wistia", "Vimeo",
    "Webflow", "Squarespace", "Wix", "Shopify", "BigCommerce",

    # ── Sports & entertainment ───────────────────────────────────────────
    "DraftKings", "FanDuel", "Sorare", "Genius Sports", "Sportradar",
    "Underdog Fantasy", "PrizePicks", "Penn Entertainment", "BetMGM", "Caesars",
    "Topgolf Callaway", "Whoop", "Strava", "Garmin", "Polar",
    "Peloton", "Tonal", "Hydrow", "Mirror", "Tempo",
    "Spotify", "SiriusXM", "Pandora", "Audacy", "Wondery",
    "Patreon", "Substack", "Ghost", "Beehiiv", "ConvertKit",

    # ── Mobility & transport ────────────────────────────────────────────
    "Lyft", "Bird", "Lime", "Voi", "Tier",
    "Bolt", "Cruise", "Waymo", "Aurora Innovation", "Tusimple",
    "Embark", "Kodiak Robotics", "Plus AI", "Gatik",
    "Convoy", "Flexport", "Project44", "Flock Freight",
    "Loadsmart", "Uber Freight", "Echo Global",
    "Joby Aviation", "Archer Aviation", "Lilium",
    "BETA Technologies", "Wisk Aero", "EHang", "Volocopter",

    # ── Web3 / crypto ────────────────────────────────────────────────────
    "Coinbase", "Kraken", "Gemini", "Bitstamp", "OKX",
    "Bybit", "Bitso", "Crypto.com", "Anchorage Digital", "Fireblocks",
    "Chainalysis", "TRM Labs", "Elliptic", "Alchemy", "Infura",
    "QuickNode", "Moralis", "thirdweb", "Mythical Games", "Dapper Labs",
    "Polygon Technology", "Magic Eden", "OpenSea", "Blur", "Sky Mavis",
    "Yuga Labs", "Animoca Brands", "Solana Labs", "Avalanche", "NEAR Protocol",
    "Sui Foundation", "Aptos Labs", "Mysten Labs", "Polygon Labs", "StarkWare",

    # ── Defense / aerospace / hardware ──────────────────────────────────
    "Anduril", "Shield AI", "Palantir", "Skydio", "Saildrone",
    "Hadrian", "Vannevar Labs", "Saronic Technologies", "Castelion",
    "Epirus", "BlueHalo", "Hermeus", "Stoke Space", "Latitude",
    "K2 Space", "Loft Orbital", "Muon Space", "True Anomaly",
    "Boston Dynamics", "Figure AI", "Agility Robotics", "Sanctuary AI",
    "1X Technologies", "Apptronik", "Tesla Optimus",
    "SpaceX", "Blue Origin", "Rocket Lab", "Astra", "Relativity Space",
    "Firefly Aerospace", "ABL Space Systems", "Astranis",
    "Loft Orbital", "Spire Global", "Planet Labs", "Maxar Technologies",
    "BlackSky", "Capella Space", "ICEYE", "Umbra",

    # ── Adtech / mar-tech ────────────────────────────────────────────────
    "The Trade Desk", "MediaMath", "AppNexus", "DV360", "Magnite",
    "PubMatic", "Index Exchange", "OpenX", "Rubicon Project",
    "Iterable", "Customer.io", "Klaviyo", "Braze", "OneSignal",
    "Mixpanel", "Amplitude", "Heap", "Segment", "Pendo",
    "Sprout Social", "Hootsuite", "Buffer", "Later", "Loomly",
    "Khoros", "Sprinklr", "Brandwatch", "Talkwalker", "Meltwater",
    "AdRoll", "Criteo", "Quantcast", "Lotame", "BlueKai",

    # ── HR tech / people ops ─────────────────────────────────────────────
    "Lattice", "15Five", "Culture Amp", "Glint", "Officevibe",
    "Greenhouse", "Lever", "Ashby", "Workable", "JazzHR",
    "Gem", "Bullhorn", "Recruitee", "BambooHR", "Personio",
    "Hibob", "Charthop", "Pave", "Comprehensive", "Carta",
    "Justworks", "Gusto", "Rippling", "Deel", "Remote",
    "Velocity Global", "Globalization Partners", "Multiplier", "Oyster",
    "Pulley", "Vouch", "Otter", "Cove",
    "Coursera for Business", "Udemy Business", "LinkedIn Learning",
    "BetterUp", "Maven", "Section", "On Deck",
]
