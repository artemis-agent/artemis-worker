"""Company discovery sources — static lists + dynamic APIs."""

import logging
import re

import httpx

from artemis.core.config import settings

logger = logging.getLogger("artemis.discovery.sources")


FORTUNE_500_COMPANIES = [
    # ── Technology / Software / Internet ──
    {"name": "Apple", "careers_hint": "jobs.apple.com"},
    {"name": "Amazon", "careers_hint": "amazon.jobs"},
    {"name": "Google", "careers_hint": "careers.google.com"},
    {"name": "Microsoft", "careers_hint": "careers.microsoft.com"},
    {"name": "Meta", "careers_hint": "metacareers.com"},
    {"name": "Nvidia", "careers_hint": "nvidia.com/careers"},
    {"name": "Tesla", "careers_hint": "tesla.com/careers"},
    {"name": "Salesforce", "careers_hint": "careers.salesforce.com"},
    {"name": "Adobe", "careers_hint": "adobe.com/careers"},
    {"name": "Oracle", "careers_hint": "oracle.com/careers"},
    {"name": "Intel", "careers_hint": "intel.com/careers"},
    {"name": "Cisco", "careers_hint": "jobs.cisco.com"},
    {"name": "IBM", "careers_hint": "ibm.com/careers"},
    {"name": "Netflix", "careers_hint": "jobs.netflix.com"},
    {"name": "Uber", "careers_hint": "uber.com/careers"},
    {"name": "Airbnb", "careers_hint": "careers.airbnb.com"},
    {"name": "Lyft", "careers_hint": "lyft.com/careers"},
    {"name": "DoorDash", "careers_hint": "doordash.com/careers"},
    {"name": "Snap", "careers_hint": "snap.com/jobs"},
    {"name": "Pinterest", "careers_hint": "careers.pinterest.com"},
    {"name": "Reddit", "careers_hint": "redditinc.com/careers"},
    {"name": "X (Twitter)", "careers_hint": "careers.x.com"},
    {"name": "LinkedIn", "careers_hint": "careers.linkedin.com"},
    {"name": "PayPal", "careers_hint": "careers.pypl.com"},
    {"name": "Block", "careers_hint": "block.xyz/careers"},
    {"name": "Shopify", "careers_hint": "shopify.com/careers"},
    {"name": "Spotify", "careers_hint": "lifeatspotify.com"},
    {"name": "Dropbox", "careers_hint": "dropbox.com/jobs"},
    {"name": "Zoom", "careers_hint": "careers.zoom.us"},
    {"name": "Slack", "careers_hint": "slack.com/careers"},
    {"name": "Atlassian", "careers_hint": "atlassian.com/company/careers"},
    {"name": "Workday", "careers_hint": "workday.com/en-us/company/careers.html"},
    {"name": "ServiceNow", "careers_hint": "servicenow.com/company/careers.html"},
    {"name": "Snowflake", "careers_hint": "snowflake.com/careers"},
    {"name": "Stripe", "careers_hint": "stripe.com/jobs"},
    {"name": "Cloudflare", "careers_hint": "cloudflare.com/careers"},
    {"name": "Palantir", "careers_hint": "palantir.com/careers"},
    {"name": "Datadog", "careers_hint": "datadoghq.com/careers"},
    {"name": "MongoDB", "careers_hint": "mongodb.com/careers"},
    {"name": "Twilio", "careers_hint": "twilio.com/company/jobs"},
    {"name": "Okta", "careers_hint": "okta.com/company/careers"},
    {"name": "Zscaler", "careers_hint": "zscaler.com/careers"},
    {"name": "CrowdStrike", "careers_hint": "crowdstrike.com/about-us/careers"},
    {"name": "Palo Alto Networks", "careers_hint": "paloaltonetworks.com/company/careers"},
    {"name": "Fortinet", "careers_hint": "fortinet.com/corporate/careers"},
    {"name": "VMware", "careers_hint": "careers.vmware.com"},
    {"name": "Splunk", "careers_hint": "splunk.com/careers"},
    {"name": "Box", "careers_hint": "box.com/careers"},
    {"name": "Asana", "careers_hint": "asana.com/jobs"},
    {"name": "HubSpot", "careers_hint": "hubspot.com/careers"},
    {"name": "Zendesk", "careers_hint": "zendesk.com/jobs"},
    {"name": "Coupa", "careers_hint": "coupa.com/careers"},
    {"name": "Procore", "careers_hint": "procore.com/jobs"},
    {"name": "Veeva", "careers_hint": "veeva.com/careers"},
    {"name": "Cadence", "careers_hint": "cadence.com/careers"},
    {"name": "Synopsys", "careers_hint": "synopsys.com/careers"},
    {"name": "Ansys", "careers_hint": "ansys.com/company/careers"},
    {"name": "Autodesk", "careers_hint": "autodesk.com/careers"},
    {"name": "PTC", "careers_hint": "ptc.com/careers"},
    {"name": "Roblox", "careers_hint": "careers.roblox.com"},
    {"name": "Unity", "careers_hint": "careers.unity.com"},
    {"name": "Electronic Arts", "careers_hint": "ea.com/careers"},
    {"name": "Activision Blizzard", "careers_hint": "careers.activisionblizzard.com"},
    {"name": "Take-Two Interactive", "careers_hint": "take2games.com/careers"},
    {"name": "Booking Holdings", "careers_hint": "booking.com/careers"},
    {"name": "Expedia", "careers_hint": "lifeatexpediagroup.com"},
    {"name": "eBay", "careers_hint": "careers.ebayinc.com"},
    {"name": "Etsy", "careers_hint": "careers.etsy.com"},
    {"name": "Wayfair", "careers_hint": "wayfair.com/careers"},
    {"name": "Yelp", "careers_hint": "yelp.careers"},
    {"name": "Match Group", "careers_hint": "mtch.com/careers"},
    {"name": "Zillow", "careers_hint": "zillow.com/careers"},

    # ── Semiconductors ──
    {"name": "AMD", "careers_hint": "careers.amd.com"},
    {"name": "Qualcomm", "careers_hint": "qualcomm.com/company/careers"},
    {"name": "Broadcom", "careers_hint": "broadcom.com/company/careers"},
    {"name": "Texas Instruments", "careers_hint": "careers.ti.com"},
    {"name": "Micron", "careers_hint": "micron.com/careers"},
    {"name": "Applied Materials", "careers_hint": "appliedmaterials.com/us/en/careers.html"},
    {"name": "Lam Research", "careers_hint": "lamresearch.com/careers"},
    {"name": "KLA", "careers_hint": "kla.com/careers"},
    {"name": "Marvell", "careers_hint": "marvell.com/company/careers"},
    {"name": "Analog Devices", "careers_hint": "analog.com/en/about-adi/careers.html"},
    {"name": "NXP", "careers_hint": "nxp.com/company/careers"},
    {"name": "ON Semiconductor", "careers_hint": "onsemi.com/careers"},
    {"name": "Microchip Technology", "careers_hint": "microchip.com/about/careers"},
    {"name": "Western Digital", "careers_hint": "westerndigital.com/company/careers"},
    {"name": "Seagate", "careers_hint": "seagate.com/careers"},
    {"name": "Skyworks", "careers_hint": "skyworksinc.com/careers"},

    # ── Financial Services / Banking ──
    {"name": "JPMorgan Chase", "careers_hint": "careers.jpmorgan.com"},
    {"name": "Bank of America", "careers_hint": "careers.bankofamerica.com"},
    {"name": "Wells Fargo", "careers_hint": "wellsfargojobs.com"},
    {"name": "Citigroup", "careers_hint": "jobs.citi.com"},
    {"name": "Goldman Sachs", "careers_hint": "goldmansachs.com/careers"},
    {"name": "Morgan Stanley", "careers_hint": "morganstanley.com/careers"},
    {"name": "American Express", "careers_hint": "americanexpress.com/en-us/careers"},
    {"name": "Capital One", "careers_hint": "capitalonecareers.com"},
    {"name": "U.S. Bancorp", "careers_hint": "careers.usbank.com"},
    {"name": "PNC Financial", "careers_hint": "pnc.jobs"},
    {"name": "Charles Schwab", "careers_hint": "aboutschwab.com/careers"},
    {"name": "Fidelity Investments", "careers_hint": "jobs.fidelity.com"},
    {"name": "BlackRock", "careers_hint": "careers.blackrock.com"},
    {"name": "State Street", "careers_hint": "statestreet.com/about-us/careers"},
    {"name": "BNY Mellon", "careers_hint": "bnymellon.com/careers"},
    {"name": "Truist", "careers_hint": "careers.truist.com"},
    {"name": "USAA", "careers_hint": "usaajobs.com"},
    {"name": "TD Ameritrade", "careers_hint": "amtdcareers.com"},
    {"name": "Northern Trust", "careers_hint": "northerntrust.com/careers"},
    {"name": "Discover Financial", "careers_hint": "mycareer.discover.com"},
    {"name": "Synchrony Financial", "careers_hint": "synchronycareers.com"},
    {"name": "Ally Financial", "careers_hint": "ally.com/about/careers"},
    {"name": "Visa", "careers_hint": "visa.com/careers"},
    {"name": "Mastercard", "careers_hint": "mastercard.com/careers"},
    {"name": "Robinhood", "careers_hint": "robinhood.com/us/en/careers"},
    {"name": "Coinbase", "careers_hint": "coinbase.com/careers"},
    {"name": "Marsh McLennan", "careers_hint": "mmc.com/careers"},
    {"name": "Aon", "careers_hint": "aon.com/about-aon/careers"},
    {"name": "Willis Towers Watson", "careers_hint": "wtwco.com/en-us/careers"},
    {"name": "Allstate", "careers_hint": "allstate.jobs"},
    {"name": "Progressive", "careers_hint": "progressive.com/careers"},
    {"name": "Travelers", "careers_hint": "careers.travelers.com"},
    {"name": "AIG", "careers_hint": "aig.com/careers"},
    {"name": "Chubb", "careers_hint": "chubb.com/us-en/about-chubb/careers.html"},
    {"name": "MetLife", "careers_hint": "metlife.com/about-us/careers"},
    {"name": "Prudential", "careers_hint": "jobs.prudential.com"},
    {"name": "Lincoln Financial", "careers_hint": "lfg.com/public/aboutus/careers"},
    {"name": "S&P Global", "careers_hint": "spglobal.com/en/who-we-are/careers"},
    {"name": "Moody's", "careers_hint": "moodys.com/careers"},
    {"name": "Nasdaq", "careers_hint": "nasdaq.com/about/careers"},
    {"name": "Intercontinental Exchange", "careers_hint": "ice.com/careers"},

    # ── Healthcare / Pharma / Biotech ──
    {"name": "UnitedHealth Group", "careers_hint": "careers.unitedhealthgroup.com"},
    {"name": "CVS Health", "careers_hint": "jobs.cvshealth.com"},
    {"name": "Anthem", "careers_hint": "careers.antheminc.com"},
    {"name": "Centene", "careers_hint": "jobs.centene.com"},
    {"name": "Humana", "careers_hint": "careers.humana.com"},
    {"name": "Cigna", "careers_hint": "jobs.thecignagroup.com"},
    {"name": "HCA Healthcare", "careers_hint": "careers.hcahealthcare.com"},
    {"name": "Cardinal Health", "careers_hint": "cardinalhealth.com/en/careers.html"},
    {"name": "McKesson", "careers_hint": "mckesson.com/careers"},
    {"name": "AmerisourceBergen", "careers_hint": "amerisourcebergen.com/careers"},
    {"name": "Walgreens Boots Alliance", "careers_hint": "jobs.walgreens.com"},
    {"name": "Johnson & Johnson", "careers_hint": "jobs.jnj.com"},
    {"name": "Pfizer", "careers_hint": "pfizer.com/about/careers"},
    {"name": "Merck", "careers_hint": "jobs.merck.com"},
    {"name": "Eli Lilly", "careers_hint": "careers.lilly.com"},
    {"name": "AbbVie", "careers_hint": "careers.abbvie.com"},
    {"name": "Bristol Myers Squibb", "careers_hint": "careers.bms.com"},
    {"name": "Amgen", "careers_hint": "careers.amgen.com"},
    {"name": "Gilead Sciences", "careers_hint": "gilead.com/careers"},
    {"name": "Biogen", "careers_hint": "biogen.com/careers"},
    {"name": "Regeneron", "careers_hint": "careers.regeneron.com"},
    {"name": "Vertex Pharmaceuticals", "careers_hint": "vrtx.com/careers"},
    {"name": "Moderna", "careers_hint": "modernatx.com/careers"},
    {"name": "Thermo Fisher Scientific", "careers_hint": "jobs.thermofisher.com"},
    {"name": "Danaher", "careers_hint": "jobs.danaher.com"},
    {"name": "Abbott", "careers_hint": "abbott.com/careers"},
    {"name": "Medtronic", "careers_hint": "medtronic.com/us-en/about/careers.html"},
    {"name": "Stryker", "careers_hint": "careers.stryker.com"},
    {"name": "Becton Dickinson", "careers_hint": "jobs.bd.com"},
    {"name": "Boston Scientific", "careers_hint": "bostonscientific.com/en-US/careers.html"},
    {"name": "Edwards Lifesciences", "careers_hint": "edwards.com/aboutus/careers"},
    {"name": "Intuitive Surgical", "careers_hint": "intuitive.com/en-us/about-us/careers"},
    {"name": "Illumina", "careers_hint": "illumina.com/company/careers.html"},
    {"name": "Genentech", "careers_hint": "careers.gene.com"},
    {"name": "23andMe", "careers_hint": "23andme.com/careers"},

    # ── Retail / Consumer Goods ──
    {"name": "Walmart", "careers_hint": "careers.walmart.com"},
    {"name": "Costco", "careers_hint": "costco.com/careers.html"},
    {"name": "Target", "careers_hint": "corporate.target.com/careers"},
    {"name": "Home Depot", "careers_hint": "careers.homedepot.com"},
    {"name": "Lowe's", "careers_hint": "talent.lowes.com"},
    {"name": "Best Buy", "careers_hint": "jobs.bestbuy.com"},
    {"name": "TJX Companies", "careers_hint": "jobs.tjx.com"},
    {"name": "Kroger", "careers_hint": "jobs.kroger.com"},
    {"name": "Albertsons", "careers_hint": "careers.albertsons.com"},
    {"name": "Dollar General", "careers_hint": "careers.dollargeneral.com"},
    {"name": "Dollar Tree", "careers_hint": "dollartreeinfo.com/careers"},
    {"name": "Macy's", "careers_hint": "macysjobs.com"},
    {"name": "Nordstrom", "careers_hint": "careers.nordstrom.com"},
    {"name": "Kohl's", "careers_hint": "careers.kohls.com"},
    {"name": "Gap", "careers_hint": "gapinc.com/en-us/careers"},
    {"name": "Levi Strauss", "careers_hint": "levistrauss.com/careers"},
    {"name": "Ross Stores", "careers_hint": "jobs.rossstores.com"},
    {"name": "Burlington", "careers_hint": "careers.burlington.com"},
    {"name": "Procter & Gamble", "careers_hint": "pgcareers.com"},
    {"name": "Unilever", "careers_hint": "careers.unilever.com"},
    {"name": "Colgate-Palmolive", "careers_hint": "jobs.colgatepalmolive.com"},
    {"name": "Kimberly-Clark", "careers_hint": "careersatkc.com"},
    {"name": "Clorox", "careers_hint": "thecloroxcompany.com/careers"},
    {"name": "Estée Lauder", "careers_hint": "elcompanies.com/en/careers"},
    {"name": "L'Oreal", "careers_hint": "careers.loreal.com"},
    {"name": "Coty", "careers_hint": "careers.coty.com"},
    {"name": "Coca-Cola", "careers_hint": "careers.coca-colacompany.com"},
    {"name": "PepsiCo", "careers_hint": "pepsicojobs.com"},
    {"name": "Mondelez", "careers_hint": "mondelezinternational.com/careers"},
    {"name": "General Mills", "careers_hint": "careers.generalmills.com"},
    {"name": "Kellogg's", "careers_hint": "careers.kellanova.com"},
    {"name": "Kraft Heinz", "careers_hint": "kraftheinzcompany.com/careers.html"},
    {"name": "Hershey", "careers_hint": "thehersheycompany.com/en_us/careers"},
    {"name": "Tyson Foods", "careers_hint": "jobs.tysonfoods.com"},
    {"name": "Conagra Brands", "careers_hint": "careersatconagrabrands.com"},
    {"name": "Campbell Soup", "careers_hint": "careers.campbellsoupcompany.com"},
    {"name": "Anheuser-Busch", "careers_hint": "anheuser-busch.com/careers"},
    {"name": "Constellation Brands", "careers_hint": "cbrands.com/careers"},
    {"name": "Molson Coors", "careers_hint": "molsoncoors.com/careers"},
    {"name": "Diageo", "careers_hint": "diageo.com/en/careers"},
    {"name": "Brown-Forman", "careers_hint": "brown-forman.com/careers"},
    {"name": "Philip Morris International", "careers_hint": "pmi.com/careers"},
    {"name": "Altria", "careers_hint": "altria.com/careers"},
    {"name": "Nike", "careers_hint": "jobs.nike.com"},
    {"name": "Adidas", "careers_hint": "careers.adidas-group.com"},
    {"name": "Under Armour", "careers_hint": "careers.underarmour.com"},
    {"name": "Lululemon", "careers_hint": "careers.lululemon.com"},
    {"name": "Starbucks", "careers_hint": "starbucks.com/careers"},
    {"name": "McDonald's", "careers_hint": "careers.mcdonalds.com"},
    {"name": "Chipotle", "careers_hint": "jobs.chipotle.com"},
    {"name": "Yum! Brands", "careers_hint": "jobs.yum.com"},
    {"name": "Domino's", "careers_hint": "jobs.dominos.com"},

    # ── Industrial / Manufacturing ──
    {"name": "Boeing", "careers_hint": "jobs.boeing.com"},
    {"name": "Lockheed Martin", "careers_hint": "lockheedmartinjobs.com"},
    {"name": "Northrop Grumman", "careers_hint": "careers.northropgrumman.com"},
    {"name": "Raytheon Technologies", "careers_hint": "careers.rtx.com"},
    {"name": "General Dynamics", "careers_hint": "gd.com/careers"},
    {"name": "L3Harris", "careers_hint": "careers.l3harris.com"},
    {"name": "Honeywell", "careers_hint": "careers.honeywell.com"},
    {"name": "GE Aerospace", "careers_hint": "jobs.gecareers.com"},
    {"name": "Caterpillar", "careers_hint": "careers.caterpillar.com"},
    {"name": "Deere & Company", "careers_hint": "careers.deere.com"},
    {"name": "3M", "careers_hint": "careers.3m.com"},
    {"name": "Emerson Electric", "careers_hint": "emerson.com/en-us/careers"},
    {"name": "Eaton", "careers_hint": "eaton.com/careers"},
    {"name": "Parker Hannifin", "careers_hint": "parker.com/portal/site/PARKER/menuitem/careers"},
    {"name": "Illinois Tool Works", "careers_hint": "itw.com/careers"},
    {"name": "Cummins", "careers_hint": "cummins.com/careers"},
    {"name": "Whirlpool", "careers_hint": "careers.whirlpoolcorp.com"},
    {"name": "Stanley Black & Decker", "careers_hint": "stanleyblackanddecker.com/careers"},
    {"name": "Dover", "careers_hint": "dovercorporation.com/careers"},
    {"name": "Rockwell Automation", "careers_hint": "rockwellautomation.com/en-us/company/careers.html"},
    {"name": "Westinghouse", "careers_hint": "westinghousenuclear.com/careers"},
    {"name": "Carrier", "careers_hint": "carrier.com/corporate/en/us/careers"},
    {"name": "Otis Worldwide", "careers_hint": "otis.com/en/us/careers"},
    {"name": "Trane Technologies", "careers_hint": "tranetechnologies.com/en/index/careers.html"},
    {"name": "Johnson Controls", "careers_hint": "johnsoncontrols.com/careers"},

    # ── Energy / Oil & Gas / Utilities ──
    {"name": "ExxonMobil", "careers_hint": "exxonmobil.com/Careers"},
    {"name": "Chevron", "careers_hint": "careers.chevron.com"},
    {"name": "ConocoPhillips", "careers_hint": "conocophillips.com/careers"},
    {"name": "Phillips 66", "careers_hint": "phillips66.com/careers"},
    {"name": "Marathon Petroleum", "careers_hint": "marathonpetroleum.com/careers"},
    {"name": "Valero Energy", "careers_hint": "careers.valero.com"},
    {"name": "Occidental Petroleum", "careers_hint": "oxy.com/careers"},
    {"name": "EOG Resources", "careers_hint": "eogresources.com/careers"},
    {"name": "Pioneer Natural Resources", "careers_hint": "pxd.com/careers"},
    {"name": "Schlumberger", "careers_hint": "careers.slb.com"},
    {"name": "Halliburton", "careers_hint": "halliburton.com/careers"},
    {"name": "Baker Hughes", "careers_hint": "bakerhughes.com/careers"},
    {"name": "NextEra Energy", "careers_hint": "nexteraenergy.com/careers.html"},
    {"name": "Duke Energy", "careers_hint": "duke-energy.com/our-company/careers"},
    {"name": "Southern Company", "careers_hint": "southerncompany.com/careers"},
    {"name": "Dominion Energy", "careers_hint": "dominionenergy.com/careers"},
    {"name": "American Electric Power", "careers_hint": "aep.com/careers"},
    {"name": "Exelon", "careers_hint": "careers.exeloncorp.com"},
    {"name": "Sempra Energy", "careers_hint": "sempra.com/careers"},
    {"name": "Xcel Energy", "careers_hint": "xcelenergy.com/careers"},
    {"name": "Constellation Energy", "careers_hint": "constellationenergy.com/careers"},

    # ── Telecom / Media / Entertainment ──
    {"name": "AT&T", "careers_hint": "att.jobs"},
    {"name": "Verizon", "careers_hint": "mycareer.verizon.com"},
    {"name": "T-Mobile", "careers_hint": "careers.t-mobile.com"},
    {"name": "Comcast", "careers_hint": "jobs.comcast.com"},
    {"name": "Charter Communications", "careers_hint": "jobs.spectrum.com"},
    {"name": "Disney", "careers_hint": "disneycareers.com"},
    {"name": "Warner Bros. Discovery", "careers_hint": "careers.wbd.com"},
    {"name": "Paramount Global", "careers_hint": "careers.paramount.com"},
    {"name": "Fox Corporation", "careers_hint": "thefoxcareers.com"},
    {"name": "NBCUniversal", "careers_hint": "nbcunicareers.com"},
    {"name": "iHeartMedia", "careers_hint": "iheartmediacareers.com"},
    {"name": "Live Nation Entertainment", "careers_hint": "careers.livenationentertainment.com"},
    {"name": "Liberty Media", "careers_hint": "libertymedia.com/careers"},
    {"name": "Lumen Technologies", "careers_hint": "jobs.lumen.com"},

    # ── Transportation / Logistics ──
    {"name": "FedEx", "careers_hint": "careers.fedex.com"},
    {"name": "UPS", "careers_hint": "jobs-ups.com"},
    {"name": "Union Pacific", "careers_hint": "up.jobs"},
    {"name": "Norfolk Southern", "careers_hint": "norfolksouthern.jobs"},
    {"name": "CSX", "careers_hint": "csx.com/index.cfm/about-us/careers"},
    {"name": "Delta Air Lines", "careers_hint": "delta.com/us/en/about-delta/careers"},
    {"name": "American Airlines", "careers_hint": "jobs.aa.com"},
    {"name": "United Airlines", "careers_hint": "careers.united.com"},
    {"name": "Southwest Airlines", "careers_hint": "careers.southwestair.com"},
    {"name": "JetBlue Airways", "careers_hint": "careers.jetblue.com"},
    {"name": "Alaska Air Group", "careers_hint": "careers.alaskaair.com"},
    {"name": "Carnival", "careers_hint": "carnival.com/about-carnival/careers"},
    {"name": "Royal Caribbean", "careers_hint": "careers.royalcaribbean.com"},
    {"name": "Hertz", "careers_hint": "hertz.com/rentacar/abouthertz/index.jsp?targetPage=hertzCareers.jsp"},
    {"name": "Avis Budget", "careers_hint": "avisbudgetgroup.com/careers"},
    {"name": "Uber Freight", "careers_hint": "uberfreight.com/careers"},
    {"name": "Maersk", "careers_hint": "maersk.com/careers"},
    {"name": "XPO Logistics", "careers_hint": "xpo.com/careers"},
    {"name": "C.H. Robinson", "careers_hint": "chrobinson.com/en-us/about-us/careers"},
    {"name": "J.B. Hunt", "careers_hint": "jbhunt.jobs"},
    {"name": "Old Dominion Freight Line", "careers_hint": "odfl.com/careers"},
    {"name": "Penske", "careers_hint": "penske.jobs"},

    # ── Automotive ──
    {"name": "Ford", "careers_hint": "corporate.ford.com/careers.html"},
    {"name": "General Motors", "careers_hint": "careers.gm.com"},
    {"name": "Stellantis", "careers_hint": "stellantis.com/en/careers"},
    {"name": "Rivian", "careers_hint": "rivian.com/careers"},
    {"name": "Lucid Motors", "careers_hint": "lucidmotors.com/careers"},
    {"name": "Toyota", "careers_hint": "careers.toyota.com"},
    {"name": "Honda", "careers_hint": "careers.honda.com"},
    {"name": "Nissan", "careers_hint": "nissanusa.com/careers.html"},
    {"name": "Subaru", "careers_hint": "subaru.com/careers"},
    {"name": "BMW", "careers_hint": "bmwgroup.jobs"},
    {"name": "Mercedes-Benz", "careers_hint": "careers.mbusa.com"},
    {"name": "Volkswagen", "careers_hint": "volkswagengroupofamerica.com/careers"},
    {"name": "Volvo", "careers_hint": "volvocars.com/intl/v/careers"},
    {"name": "Aptiv", "careers_hint": "aptiv.com/en/careers"},
    {"name": "BorgWarner", "careers_hint": "borgwarner.com/careers"},
    {"name": "Magna", "careers_hint": "magna.com/careers"},
    {"name": "AutoZone", "careers_hint": "careers.autozone.com"},
    {"name": "O'Reilly Auto Parts", "careers_hint": "corporate.oreillyauto.com/onlinecareers"},
    {"name": "Carvana", "careers_hint": "careers.carvana.com"},
    {"name": "AutoNation", "careers_hint": "autonation.jobs"},

    # ── Hospitality / Real Estate ──
    {"name": "Marriott", "careers_hint": "careers.marriott.com"},
    {"name": "Hilton", "careers_hint": "jobs.hilton.com"},
    {"name": "Hyatt", "careers_hint": "careers.hyatt.com"},
    {"name": "MGM Resorts", "careers_hint": "mgmresortscareers.com"},
    {"name": "Caesars Entertainment", "careers_hint": "caesars.com/corporate/careers"},
    {"name": "Wynn Resorts", "careers_hint": "wynncareers.com"},
    {"name": "Las Vegas Sands", "careers_hint": "sands.com/careers.html"},
    {"name": "CBRE", "careers_hint": "careers.cbre.com"},
    {"name": "JLL", "careers_hint": "jll.com/en/careers"},
    {"name": "Cushman & Wakefield", "careers_hint": "cushmanwakefield.com/en/about-us/careers"},
    {"name": "Prologis", "careers_hint": "prologis.com/careers"},
    {"name": "Simon Property Group", "careers_hint": "simon.com/careers"},
    {"name": "Equinix", "careers_hint": "equinix.com/careers"},
    {"name": "American Tower", "careers_hint": "americantower.com/about/careers"},
    {"name": "Crown Castle", "careers_hint": "crowncastle.com/about-us/careers"},

    # ── Consulting / Professional Services ──
    {"name": "Accenture", "careers_hint": "accenture.com/us-en/careers"},
    {"name": "Deloitte", "careers_hint": "apply.deloitte.com"},
    {"name": "PwC", "careers_hint": "pwc.com/us/en/careers.html"},
    {"name": "EY", "careers_hint": "ey.com/en_us/careers"},
    {"name": "KPMG", "careers_hint": "kpmguscareers.com"},
    {"name": "McKinsey", "careers_hint": "mckinsey.com/careers"},
    {"name": "Boston Consulting Group", "careers_hint": "careers.bcg.com"},
    {"name": "Bain & Company", "careers_hint": "bain.com/careers"},
    {"name": "Booz Allen Hamilton", "careers_hint": "careers.boozallen.com"},
    {"name": "Capgemini", "careers_hint": "capgemini.com/us-en/careers"},
    {"name": "Cognizant", "careers_hint": "careers.cognizant.com"},
    {"name": "Infosys", "careers_hint": "infosys.com/careers"},
    {"name": "Tata Consultancy Services", "careers_hint": "tcs.com/careers"},
    {"name": "Wipro", "careers_hint": "careers.wipro.com"},
    {"name": "DXC Technology", "careers_hint": "dxc.com/us/en/careers"},
    {"name": "CGI", "careers_hint": "cgi.com/en/careers"},
    {"name": "ManpowerGroup", "careers_hint": "manpowergroup.com/careers"},
    {"name": "Robert Half", "careers_hint": "roberthalf.com/about-rh/careers"},
    {"name": "Korn Ferry", "careers_hint": "kornferry.com/careers"},
    {"name": "ADP", "careers_hint": "jobs.adp.com"},
    {"name": "Paychex", "careers_hint": "paychex.com/about/careers"},
    {"name": "Gartner", "careers_hint": "jobs.gartner.com"},

    # ── Construction / Materials ──
    {"name": "Lennar", "careers_hint": "lennarcareers.com"},
    {"name": "D.R. Horton", "careers_hint": "drhorton.com/careers"},
    {"name": "PulteGroup", "careers_hint": "pultegroupinc.com/careers"},
    {"name": "Nucor", "careers_hint": "careers.nucor.com"},
    {"name": "Vulcan Materials", "careers_hint": "careers.vulcanmaterials.com"},
    {"name": "Martin Marietta", "careers_hint": "martinmarietta.com/careers"},
    {"name": "Sherwin-Williams", "careers_hint": "careers.sherwin-williams.com"},
    {"name": "PPG Industries", "careers_hint": "careers.ppg.com"},
    {"name": "Air Products", "careers_hint": "airproducts.com/careers"},
    {"name": "Praxair", "careers_hint": "linde.com/careers"},
    {"name": "Linde", "careers_hint": "linde.com/careers"},
    {"name": "Dow", "careers_hint": "careers.dow.com"},
    {"name": "DuPont", "careers_hint": "careers.dupont.com"},
    {"name": "Corteva", "careers_hint": "corteva.com/careers"},
    {"name": "International Paper", "careers_hint": "internationalpaper.com/careers"},
    {"name": "Westrock", "careers_hint": "westrock.com/careers"},

    # ── Misc large employers ──
    {"name": "Allegion", "careers_hint": "allegion.com/corp/en/careers.html"},
    {"name": "Fastenal", "careers_hint": "fastenal.jobs"},
    {"name": "W.W. Grainger", "careers_hint": "careers.grainger.com"},
    {"name": "Sysco", "careers_hint": "syscocareers.com"},
    {"name": "US Foods", "careers_hint": "usfoods.com/our-company/careers.html"},
    {"name": "Performance Food Group", "careers_hint": "pfgc.com/Careers"},
    {"name": "Aramark", "careers_hint": "careers.aramark.com"},
    {"name": "Compass Group", "careers_hint": "compass-usa.com/careers"},
    {"name": "Cintas", "careers_hint": "careers.cintas.com"},
    {"name": "Waste Management", "careers_hint": "careers.wm.com"},
    {"name": "Republic Services", "careers_hint": "republicservices.com/careers"},
    {"name": "Republic Airways", "careers_hint": "rjet.com/careers"},
]


CLOUD_100_COMPANIES = [
    {"name": "Databricks", "careers_hint": "databricks.com/careers"},
    {"name": "Canva", "careers_hint": "canva.com/careers"},
    {"name": "Figma", "careers_hint": "figma.com/careers"},
    {"name": "Notion", "careers_hint": "notion.so/careers"},
    {"name": "Airtable", "careers_hint": "airtable.com/careers"},
    {"name": "Vercel", "careers_hint": "vercel.com/careers"},
    {"name": "Linear", "careers_hint": "linear.app/careers"},
    {"name": "Retool", "careers_hint": "retool.com/careers"},
    {"name": "Supabase", "careers_hint": "supabase.com/careers"},
    {"name": "PostHog", "careers_hint": "posthog.com/careers"},
]


# ── Dynamic sources ───────────────────────────────────────────────────────

async def fetch_crunchbase_top(limit: int = 100) -> list[dict]:
    """Fetch top companies from Crunchbase API v4 (ranked by org rank).

    Paginates with `after_id` cursor to support > 1000 results.
    """
    key = settings.crunchbase_api_key
    if not key:
        logger.warning("CRUNCHBASE_API_KEY not set, skipping")
        return []

    PAGE_SIZE = 1000  # API max
    results: list[dict] = []
    after_id: str | None = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        while len(results) < limit:
            payload = {
                "field_ids": ["identifier", "short_description", "website_url"],
                "order": [{"field_id": "rank_org", "sort": "asc"}],
                "limit": min(PAGE_SIZE, limit - len(results)),
            }
            if after_id:
                payload["after_id"] = after_id

            resp = await client.post(
                "https://api.crunchbase.com/api/v4/searches/organizations",
                headers={"X-cb-user-key": key, "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code != 200:
                logger.error(f"Crunchbase API error {resp.status_code}: {resp.text[:200]}")
                break

            data = resp.json()
            entities = data.get("entities") or []
            if not entities:
                break

            for entity in entities:
                props = entity.get("properties", {})
                ident = props.get("identifier", {})
                name = ident.get("value", "")
                website = props.get("website_url", "")
                if name:
                    results.append({"name": name, "website": website, "source": "crunchbase"})

            # Pagination: use last entity's uuid as after_id
            after_id = entities[-1].get("uuid")
            if not after_id or len(entities) < PAGE_SIZE:
                break

    logger.info(f"fetched {len(results)} companies from Crunchbase")
    return results[:limit]


_CB_PERMALINK_RE = re.compile(
    r"crunchbase\.com/organization/([a-z0-9][a-z0-9-]*)",
    re.IGNORECASE,
)


async def fetch_crunchbase_website(slug_or_url: str) -> str | None:
    """Resolve a Crunchbase organization (permalink slug or profile URL)
    to its official website URL via the Crunchbase API v4.

    Returns the `website_url` field, or None if the API key is missing,
    the org isn't found, or the response has no website on file.

    Uses the `/searches/organizations` endpoint with a permalink equality
    predicate \u2014 the `/entities/organizations/{id}` endpoint requires a
    higher API tier than the default Crunchbase plan.

    Examples:
        await fetch_crunchbase_website("yubico")
        await fetch_crunchbase_website("https://www.crunchbase.com/organization/yubico")
    """
    key = settings.crunchbase_api_key
    if not key:
        logger.warning("CRUNCHBASE_API_KEY not set")
        return None
    if not slug_or_url:
        return None

    # Accept either a bare permalink or a full profile URL.
    m = _CB_PERMALINK_RE.search(slug_or_url)
    permalink = (m.group(1) if m else slug_or_url).strip("/").lower()
    if "/" in permalink or not permalink:
        return None

    payload = {
        "field_ids": ["website_url", "permalink", "identifier"],
        "query": [{
            "type": "predicate",
            "field_id": "identifier",
            "operator_id": "contains",
            "values": [permalink],
        }],
        "limit": 25,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.crunchbase.com/api/v4/searches/organizations",
                headers={"X-cb-user-key": key, "Content-Type": "application/json"},
                json=payload,
            )
    except Exception as e:
        logger.warning(f"Crunchbase fetch failed for {permalink}: {e}")
        return None

    if resp.status_code != 200:
        logger.warning(
            f"Crunchbase API error {resp.status_code} for {permalink}: {resp.text[:200]}"
        )
        return None

    entities = (resp.json() or {}).get("entities") or []
    # `identifier contains` is a fuzzy match — pick the entity whose
    # permalink is an *exact* match for the requested slug.
    for ent in entities:
        props = ent.get("properties") or {}
        if (props.get("permalink") or "").lower() == permalink:
            return props.get("website_url") or None
    return None


_CB_LOGO_PREFIX = "https://images.crunchbase.com/image/upload/"


def crunchbase_logo_url(image_id: str | None) -> str | None:
    """Build a publicly-fetchable logo URL from a Crunchbase `image_id`.

    The `image_id` is the value returned inside `identifier.image_id`
    (e.g. `"v1483638230/l94zqzbvxcixwf62yord.png"`). Crunchbase serves
    the asset through `images.crunchbase.com`; the direct Cloudinary URL
    (`res.cloudinary.com/crunchbase-production/...`) returns 404.
    """
    if not image_id:
        return None
    return _CB_LOGO_PREFIX + image_id.lstrip("/")


# Fields known to work on our Crunchbase API tier. Kept as a module-level
# constant so callers / tests can reference the exact set.
_CB_PROFILE_FIELDS = [
    "identifier",          # {permalink, uuid, value (=name), image_id}
    "website_url",
    "short_description",
    "linkedin",            # {value: url}
    "twitter",             # {value: url}
    "facebook",            # {value: url}
]


async def fetch_crunchbase_profile(slug_or_url: str) -> dict | None:
    """Fetch a full profile for one Crunchbase organization.

    Same lookup mechanism as `fetch_crunchbase_website` (search +
    client-side exact-permalink filter — the `/entities/` endpoint is
    gated on our tier). Returns a flat dict ready to merge into the
    `companies` table, or None on miss / API error.

    Example return shape (keys map 1-to-1 to `Company` columns):
        {
            "crunchbase_permalink": "yubico",
            "crunchbase_uuid":      "dce5325d-f778-10ab-f2d1-ebd6dcdc00a3",
            "crunchbase_image_id":  "v1483638230/l94zqzbvxcixwf62yord.png",
            "name":                 "Yubico",
            "website":              "http://www.yubico.com",
            "logo_url":             "https://images.crunchbase.com/image/upload/v1483638230/...",
            "description":          "Yubico protects logins with hardware devices...",
            "linkedin_url":         "https://www.linkedin.com/company/yubico/",
            "twitter_url":          "https://x.com/Yubico",
            "facebook_url":         "http://www.facebook.com/Yubikey",
        }
    """
    key = settings.crunchbase_api_key
    if not key or not slug_or_url:
        return None
    m = _CB_PERMALINK_RE.search(slug_or_url)
    permalink = (m.group(1) if m else slug_or_url).strip("/").lower()
    if "/" in permalink or not permalink:
        return None

    payload = {
        "field_ids": _CB_PROFILE_FIELDS,
        "query": [{
            "type": "predicate",
            "field_id": "identifier",
            "operator_id": "contains",
            "values": [permalink],
        }],
        "limit": 25,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.crunchbase.com/api/v4/searches/organizations",
                headers={"X-cb-user-key": key, "Content-Type": "application/json"},
                json=payload,
            )
    except Exception as e:
        logger.warning(f"Crunchbase profile fetch failed for {permalink}: {e}")
        return None

    if resp.status_code != 200:
        logger.warning(
            f"Crunchbase API error {resp.status_code} for {permalink}: {resp.text[:200]}"
        )
        return None

    for ent in (resp.json() or {}).get("entities") or []:
        props = ent.get("properties") or {}
        ident = props.get("identifier") or {}
        if (ident.get("permalink") or props.get("permalink") or "").lower() != permalink:
            continue
        # Social fields come back as {"value": url}; flatten them.
        def _unwrap(field):
            v = props.get(field)
            return v.get("value") if isinstance(v, dict) else (v or None)

        return {
            "crunchbase_permalink": ident.get("permalink") or props.get("permalink"),
            "crunchbase_uuid":      ident.get("uuid") or ent.get("uuid"),
            "crunchbase_image_id":  ident.get("image_id"),
            "name":                 ident.get("value"),
            "website":              props.get("website_url") or None,
            "logo_url":             crunchbase_logo_url(ident.get("image_id")),
            "description":          props.get("short_description") or None,
            "linkedin_url":         _unwrap("linkedin"),
            "twitter_url":          _unwrap("twitter"),
            "facebook_url":         _unwrap("facebook"),
        }
    return None


async def fetch_yc_companies(limit: int = 500) -> list[dict]:
    """Fetch companies from Y Combinator's public API (paginated).

    Accepts all active companies with a website — let the ATS probe filter
    out ones that don't have a discoverable job board.
    """
    results = []
    page = 1
    per_page = 25  # YC API ignores larger per_page values and always returns 25
    OLD_BATCHES_OK = True

    def _accept(co: dict) -> bool:
        name = co.get("name", "")
        if not name:
            return False
        status = (co.get("status") or "").lower()
        if status in ("inactive", "dead"):
            return False
        # Take any active company with a website — let the ATS probe filter
        # out ones that don't have a discoverable job board.
        return bool(co.get("website"))

    async with httpx.AsyncClient(timeout=30.0) as client:
        while len(results) < limit:
            try:
                resp = await client.get(
                    "https://api.ycombinator.com/v0.1/companies",
                    params={"page": page, "per_page": per_page},
                )
            except Exception as e:
                logger.error(f"YC page {page} fetch failed: {e}")
                break
            if resp.status_code != 200:
                logger.error(f"YC API error {resp.status_code}")
                break

            data = resp.json()
            companies = data if isinstance(data, list) else data.get("companies", [])
            if not companies:
                break

            for co in companies:
                if _accept(co):
                    results.append({
                        "name": co.get("name", ""),
                        "website": co.get("website", ""),
                        "source": "yc",
                        "yc_batch": co.get("batch", ""),
                        "yc_team_size": co.get("teamSize", 0),
                    })
                    if len(results) >= limit:
                        break

            page += 1
            if len(companies) < per_page:
                break  # last page

    logger.info(f"fetched {len(results)} companies from YC ({page - 1} pages)")
    return results[:limit]


async def fetch_wellfound_companies(limit: int = 100) -> list[dict]:
    """Top startups from Wellfound (formerly AngelList Talent).

    Wellfound has no public API and blocks scraping. This is a curated list
    of top hiring startups commonly featured on the platform.
    """
    WELLFOUND_TOP = [
        {"name": "Notion", "website": "https://notion.so"},
        {"name": "Ramp", "website": "https://ramp.com"},
        {"name": "Brex", "website": "https://brex.com"},
        {"name": "Deel", "website": "https://deel.com"},
        {"name": "Mercury", "website": "https://mercury.com"},
        {"name": "Rippling", "website": "https://rippling.com"},
        {"name": "Anduril", "website": "https://anduril.com"},
        {"name": "Scale AI", "website": "https://scale.com"},
        {"name": "Anthropic", "website": "https://anthropic.com"},
        {"name": "Cohere", "website": "https://cohere.com"},
        {"name": "Mistral AI", "website": "https://mistral.ai"},
        {"name": "Perplexity", "website": "https://perplexity.ai"},
        {"name": "Replit", "website": "https://replit.com"},
        {"name": "Railway", "website": "https://railway.app"},
        {"name": "Render", "website": "https://render.com"},
        {"name": "Fly.io", "website": "https://fly.io"},
        {"name": "Neon", "website": "https://neon.tech"},
        {"name": "Turso", "website": "https://turso.tech"},
        {"name": "Temporal", "website": "https://temporal.io"},
        {"name": "Dagster", "website": "https://dagster.io"},
        {"name": "Prefect", "website": "https://prefect.io"},
        {"name": "Modal", "website": "https://modal.com"},
        {"name": "Weights & Biases", "website": "https://wandb.ai"},
        {"name": "Hugging Face", "website": "https://huggingface.co"},
        {"name": "Cursor", "website": "https://cursor.com"},
        {"name": "Codeium", "website": "https://codeium.com"},
        {"name": "Sourcegraph", "website": "https://sourcegraph.com"},
        {"name": "Grafana Labs", "website": "https://grafana.com"},
        {"name": "Kong", "website": "https://konghq.com"},
        {"name": "Tailscale", "website": "https://tailscale.com"},
        {"name": "Wiz", "website": "https://wiz.io"},
        {"name": "Snyk", "website": "https://snyk.io"},
        {"name": "1Password", "website": "https://1password.com"},
        {"name": "Bitwarden", "website": "https://bitwarden.com"},
        {"name": "Vanta", "website": "https://vanta.com"},
        {"name": "Drata", "website": "https://drata.com"},
        {"name": "Loom", "website": "https://loom.com"},
        {"name": "Miro", "website": "https://miro.com"},
        {"name": "Coda", "website": "https://coda.io"},
        {"name": "Clay", "website": "https://clay.com"},
        {"name": "Fivetran", "website": "https://fivetran.com"},
        {"name": "dbt Labs", "website": "https://getdbt.com"},
        {"name": "Airbyte", "website": "https://airbyte.com"},
        {"name": "Stytch", "website": "https://stytch.com"},
        {"name": "WorkOS", "website": "https://workos.com"},
        {"name": "Resend", "website": "https://resend.com"},
        {"name": "Inngest", "website": "https://inngest.com"},
        {"name": "Convex", "website": "https://convex.dev"},
        {"name": "Clerk", "website": "https://clerk.com"},
        {"name": "Pinecone", "website": "https://pinecone.io"},
    ]
    results = [{**c, "source": "wellfound"} for c in WELLFOUND_TOP[:limit]]
    logger.info(f"loaded {len(results)} companies from Wellfound list")
    return results


async def fetch_builtin_companies(limit: int = 100) -> list[dict]:
    """Discover companies from BuiltIn.com's best places to work lists."""
    urls = [
        "https://builtin.com/best-places-to-work",
        "https://builtin.com/companies",
    ]
    results = []
    seen = set()

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for url in urls:
            if len(results) >= limit:
                break
            try:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    continue

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                # BuiltIn company cards typically have company names in h2/h3 or specific classes
                for el in soup.select("h2 a, h3 a, [data-id] a, .company-card a"):
                    name = el.get_text().strip()
                    if name and len(name) > 2 and name not in seen:
                        seen.add(name)
                        results.append({"name": name, "source": "builtin"})
            except Exception as e:
                logger.debug(f"BuiltIn fetch failed: {e}")

    logger.info(f"fetched {len(results)} companies from BuiltIn")
    return results[:limit]


async def search_careers_page(company_name: str) -> str | None:
    """Find a company's careers page via DuckDuckGo search."""
    from urllib.parse import unquote, urlparse, parse_qs

    query = f"{company_name} careers jobs site"
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        try:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.status_code != 200:
                return None

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            for link in soup.select("a.result__a"):
                href = link.get("href", "")
                # DDG wraps URLs in redirects: //duckduckgo.com/l/?uddg=https%3A...
                actual = _extract_ddg_url(href)
                if any(kw in actual.lower() for kw in ["career", "jobs", "job-board", "greenhouse", "lever", "workday"]):
                    return actual
            # fallback: first result
            first = soup.select_one("a.result__a")
            if first:
                return _extract_ddg_url(first.get("href", ""))
        except Exception as e:
            logger.debug(f"DDG search failed for {company_name}: {e}")
    return None


def _extract_ddg_url(href: str) -> str:
    """Extract actual URL from DDG redirect wrapper."""
    from urllib.parse import unquote, urlparse, parse_qs
    if "uddg=" in href:
        parsed = parse_qs(urlparse(href).query)
        urls = parsed.get("uddg", [])
        if urls:
            return unquote(urls[0])
    if href.startswith("//"):
        return "https:" + href
    return href


def get_source_list(source: str) -> list[dict]:
    """Get a static company list by name."""
    sources = {
        "fortune500": FORTUNE_500_COMPANIES,
        "cloud100": CLOUD_100_COMPANIES,
    }
    return sources.get(source, [])


async def get_dynamic_source(source: str, limit: int = 100) -> list[dict]:
    """Fetch companies from a dynamic API source."""
    if source == "crunchbase":
        return await fetch_crunchbase_top(limit)
    elif source == "yc":
        return await fetch_yc_companies(limit)
    elif source == "wellfound":
        return await fetch_wellfound_companies(limit)
    elif source == "builtin":
        return await fetch_builtin_companies(limit)
    return []
