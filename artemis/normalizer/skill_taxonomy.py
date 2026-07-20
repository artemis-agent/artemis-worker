"""Skill taxonomy — canonical names, aliases, categories, and relationships."""

SKILL_TAXONOMY = [
    # Languages
    {
        "canonical": "Python",
        "category": "language",
        "aliases": ["python3", "py", "cpython"],
        "related": ["Django", "FastAPI", "Flask"],
    },
    {
        "canonical": "JavaScript",
        "category": "language",
        "aliases": ["js", "ecmascript", "es6", "es2015"],
        "related": ["TypeScript", "Node.js", "React"],
    },
    {
        "canonical": "TypeScript",
        "category": "language",
        "aliases": ["ts", "typescript"],
        "related": ["JavaScript", "React", "Angular"],
    },
    {
        "canonical": "Go",
        "category": "language",
        "aliases": ["golang", "go lang"],
        "related": ["Kubernetes", "Docker", "gRPC"],
    },
    {
        "canonical": "Java",
        "category": "language",
        "aliases": ["java8", "java11", "java17", "jdk", "jvm"],
        "related": ["Spring Boot", "Kotlin", "Gradle"],
    },
    {
        "canonical": "C++",
        "category": "language",
        "aliases": ["cpp", "c plus plus", "c++11", "c++14", "c++17", "c++20"],
        "related": ["C", "Rust"],
    },
    {
        "canonical": "C#",
        "category": "language",
        "aliases": ["csharp", "c sharp", "dotnet", ".net"],
        "related": [".NET Core", "Azure"],
    },
    {"canonical": "Rust", "category": "language", "aliases": ["rustlang"], "related": ["C++", "WebAssembly"]},
    {"canonical": "Ruby", "category": "language", "aliases": ["rb"], "related": ["Rails", "Sinatra"]},
    {"canonical": "Swift", "category": "language", "aliases": ["swiftui"], "related": ["iOS", "Xcode"]},
    {"canonical": "Kotlin", "category": "language", "aliases": ["kt"], "related": ["Java", "Android"]},
    {"canonical": "PHP", "category": "language", "aliases": ["php7", "php8"], "related": ["Laravel", "WordPress"]},
    {"canonical": "Scala", "category": "language", "aliases": [], "related": ["Java", "Spark", "Akka"]},
    {
        "canonical": "SQL",
        "category": "language",
        "aliases": ["structured query language"],
        "related": ["PostgreSQL", "MySQL"],
    },
    {
        "canonical": "R",
        "category": "language",
        "aliases": ["rlang", "r-lang"],
        "related": ["Data Science", "Statistics"],
    },
    # Frontend
    {
        "canonical": "React",
        "category": "frontend",
        "aliases": ["reactjs", "react.js", "react js"],
        "related": ["Next.js", "Redux", "TypeScript"],
    },
    {"canonical": "Next.js", "category": "frontend", "aliases": ["nextjs", "next"], "related": ["React", "Vercel"]},
    {
        "canonical": "Vue.js",
        "category": "frontend",
        "aliases": ["vuejs", "vue", "vue3", "vue2"],
        "related": ["Nuxt", "JavaScript"],
    },
    {
        "canonical": "Angular",
        "category": "frontend",
        "aliases": ["angularjs", "angular2", "ng"],
        "related": ["TypeScript", "RxJS"],
    },
    {"canonical": "Svelte", "category": "frontend", "aliases": ["sveltekit"], "related": ["JavaScript"]},
    {"canonical": "HTML", "category": "frontend", "aliases": ["html5"], "related": ["CSS", "JavaScript"]},
    {
        "canonical": "CSS",
        "category": "frontend",
        "aliases": ["css3", "scss", "sass", "less"],
        "related": ["Tailwind CSS", "HTML"],
    },
    {
        "canonical": "Tailwind CSS",
        "category": "frontend",
        "aliases": ["tailwind", "tailwindcss"],
        "related": ["CSS", "React"],
    },
    # Backend
    {
        "canonical": "Node.js",
        "category": "backend",
        "aliases": ["nodejs", "node", "node js"],
        "related": ["Express", "NestJS", "JavaScript"],
    },
    {
        "canonical": "Django",
        "category": "backend",
        "aliases": ["django rest framework", "drf"],
        "related": ["Python", "PostgreSQL"],
    },
    {"canonical": "FastAPI", "category": "backend", "aliases": ["fast api"], "related": ["Python", "Pydantic"]},
    {"canonical": "Flask", "category": "backend", "aliases": [], "related": ["Python"]},
    {
        "canonical": "Spring Boot",
        "category": "backend",
        "aliases": ["spring", "spring framework", "springboot"],
        "related": ["Java", "Kotlin"],
    },
    {"canonical": "Rails", "category": "backend", "aliases": ["ruby on rails", "ror"], "related": ["Ruby"]},
    {
        "canonical": ".NET Core",
        "category": "backend",
        "aliases": ["dotnet core", "asp.net", "asp.net core"],
        "related": ["C#", "Azure"],
    },
    {"canonical": "Express", "category": "backend", "aliases": ["expressjs", "express.js"], "related": ["Node.js"]},
    {"canonical": "GraphQL", "category": "backend", "aliases": ["gql"], "related": ["Apollo", "REST APIs"]},
    {
        "canonical": "REST APIs",
        "category": "backend",
        "aliases": ["rest", "restful", "restful api", "api design"],
        "related": ["GraphQL", "OpenAPI"],
    },
    {
        "canonical": "gRPC",
        "category": "backend",
        "aliases": ["grpc", "protobuf", "protocol buffers"],
        "related": ["Go", "Microservices"],
    },
    # Databases
    {
        "canonical": "PostgreSQL",
        "category": "database",
        "aliases": ["postgres", "pg", "psql"],
        "related": ["SQL", "pgvector"],
    },
    {"canonical": "MySQL", "category": "database", "aliases": ["mariadb"], "related": ["SQL"]},
    {"canonical": "MongoDB", "category": "database", "aliases": ["mongo", "nosql"], "related": ["Mongoose"]},
    {"canonical": "Redis", "category": "database", "aliases": ["redis cluster"], "related": ["Caching", "Pub/Sub"]},
    {
        "canonical": "Elasticsearch",
        "category": "database",
        "aliases": ["elastic", "es", "opensearch"],
        "related": ["Kibana", "Logstash"],
    },
    {"canonical": "DynamoDB", "category": "database", "aliases": ["dynamo"], "related": ["AWS", "NoSQL"]},
    {
        "canonical": "Cassandra",
        "category": "database",
        "aliases": ["apache cassandra"],
        "related": ["NoSQL", "Distributed Systems"],
    },
    # Cloud & Infra
    {
        "canonical": "AWS",
        "category": "cloud",
        "aliases": ["amazon web services", "amazon aws"],
        "related": ["EC2", "S3", "Lambda"],
    },
    {
        "canonical": "Azure",
        "category": "cloud",
        "aliases": ["microsoft azure", "azure cloud"],
        "related": ["C#", ".NET Core"],
    },
    {
        "canonical": "GCP",
        "category": "cloud",
        "aliases": ["google cloud", "google cloud platform"],
        "related": ["BigQuery", "Kubernetes"],
    },
    {
        "canonical": "Docker",
        "category": "infra",
        "aliases": ["container", "containerization", "dockerfile"],
        "related": ["Kubernetes", "CI/CD"],
    },
    {
        "canonical": "Kubernetes",
        "category": "infra",
        "aliases": ["k8s", "kube", "k8"],
        "related": ["Docker", "Helm", "GKE", "EKS"],
    },
    {
        "canonical": "Terraform",
        "category": "infra",
        "aliases": ["tf", "hashicorp terraform", "iac"],
        "related": ["AWS", "Infrastructure as Code"],
    },
    {
        "canonical": "CI/CD",
        "category": "infra",
        "aliases": [
            "cicd",
            "continuous integration",
            "continuous deployment",
            "github actions",
            "jenkins",
            "gitlab ci",
        ],
        "related": ["Docker", "Git"],
    },
    {
        "canonical": "Linux",
        "category": "infra",
        "aliases": ["ubuntu", "debian", "centos", "rhel"],
        "related": ["Bash", "Shell"],
    },
    # Data & ML
    {"canonical": "PyTorch", "category": "ml", "aliases": ["torch"], "related": ["Deep Learning", "Python"]},
    {"canonical": "TensorFlow", "category": "ml", "aliases": ["tf", "keras"], "related": ["Deep Learning", "Python"]},
    {
        "canonical": "Machine Learning",
        "category": "ml",
        "aliases": ["ml", "ml/ai", "ai/ml"],
        "related": ["Deep Learning", "Data Science"],
    },
    {
        "canonical": "Deep Learning",
        "category": "ml",
        "aliases": ["dl", "neural networks", "nn"],
        "related": ["PyTorch", "TensorFlow"],
    },
    {
        "canonical": "LLM",
        "category": "ml",
        "aliases": ["large language model", "llms", "generative ai", "genai", "gen ai"],
        "related": ["LangChain", "OpenAI", "RAG"],
    },
    {"canonical": "LangChain", "category": "ml", "aliases": ["langchain"], "related": ["LLM", "RAG", "Python"]},
    {
        "canonical": "NLP",
        "category": "ml",
        "aliases": ["natural language processing", "text mining"],
        "related": ["LLM", "Transformers"],
    },
    {
        "canonical": "Computer Vision",
        "category": "ml",
        "aliases": ["cv", "image recognition", "object detection"],
        "related": ["PyTorch", "OpenCV"],
    },
    {
        "canonical": "Data Science",
        "category": "data",
        "aliases": ["data analytics", "analytics"],
        "related": ["Python", "R", "SQL"],
    },
    {
        "canonical": "Spark",
        "category": "data",
        "aliases": ["apache spark", "pyspark"],
        "related": ["Data Engineering", "Scala"],
    },
    {
        "canonical": "Kafka",
        "category": "data",
        "aliases": ["apache kafka"],
        "related": ["Event Streaming", "Distributed Systems"],
    },
    {
        "canonical": "Airflow",
        "category": "data",
        "aliases": ["apache airflow"],
        "related": ["Data Engineering", "Python"],
    },
    # DevOps & Observability
    {"canonical": "Prometheus", "category": "observability", "aliases": ["prom"], "related": ["Grafana", "Monitoring"]},
    {"canonical": "Grafana", "category": "observability", "aliases": [], "related": ["Prometheus", "Observability"]},
    {"canonical": "Datadog", "category": "observability", "aliases": ["dd"], "related": ["Monitoring", "APM"]},
    {
        "canonical": "Git",
        "category": "devops",
        "aliases": ["github", "gitlab", "bitbucket", "version control"],
        "related": ["CI/CD"],
    },
    # Architecture
    {
        "canonical": "Microservices",
        "category": "architecture",
        "aliases": ["micro services", "service mesh"],
        "related": ["Kubernetes", "gRPC", "Distributed Systems"],
    },
    {
        "canonical": "Distributed Systems",
        "category": "architecture",
        "aliases": ["distributed computing"],
        "related": ["Kafka", "Microservices"],
    },
    {
        "canonical": "System Design",
        "category": "architecture",
        "aliases": ["systems design", "architecture design"],
        "related": ["Distributed Systems", "Scalability"],
    },
    {
        "canonical": "Event Streaming",
        "category": "architecture",
        "aliases": ["event driven", "event-driven architecture", "eda", "pub/sub"],
        "related": ["Kafka", "RabbitMQ"],
    },
    # Soft Skills / Methods
    {
        "canonical": "Agile",
        "category": "methodology",
        "aliases": ["scrum", "kanban", "sprint"],
        "related": ["Product Management"],
    },
    {
        "canonical": "Product Management",
        "category": "business",
        "aliases": ["product strategy", "pm"],
        "related": ["Agile", "Data Analysis"],
    },
    {
        "canonical": "Data Analysis",
        "category": "business",
        "aliases": ["data driven", "business intelligence", "bi"],
        "related": ["SQL", "Python"],
    },
    # Mobile
    {"canonical": "iOS", "category": "mobile", "aliases": ["ios development", "iphone"], "related": ["Swift", "Xcode"]},
    {"canonical": "Android", "category": "mobile", "aliases": ["android development"], "related": ["Kotlin", "Java"]},
    {
        "canonical": "React Native",
        "category": "mobile",
        "aliases": ["rn", "react-native"],
        "related": ["React", "Mobile"],
    },
    {"canonical": "Flutter", "category": "mobile", "aliases": ["dart"], "related": ["Mobile", "Cross-platform"]},
    # Security
    {
        "canonical": "Cybersecurity",
        "category": "security",
        "aliases": ["infosec", "information security", "appsec", "application security"],
        "related": ["Penetration Testing", "SIEM"],
    },
    {
        "canonical": "OAuth",
        "category": "security",
        "aliases": ["oauth2", "openid", "oidc", "saml"],
        "related": ["Authentication", "JWT"],
    },
]


def build_alias_map() -> dict[str, str]:
    """Build a lowercase alias → canonical name map."""
    alias_map: dict[str, str] = {}
    for entry in SKILL_TAXONOMY:
        canonical = entry["canonical"]
        alias_map[canonical.lower()] = canonical
        for alias in entry["aliases"]:
            alias_map[alias.lower()] = canonical
    return alias_map


_ALIAS_MAP: dict[str, str] | None = None


def normalize_skill(skill: str) -> str:
    """Normalize a skill name to its canonical form."""
    global _ALIAS_MAP
    if _ALIAS_MAP is None:
        _ALIAS_MAP = build_alias_map()
    return _ALIAS_MAP.get(skill.lower().strip(), skill.strip())


def normalize_skills(skills: list[str]) -> list[str]:
    """Normalize a list of skills, deduplicating canonical names."""
    seen = set()
    result = []
    for s in skills:
        canonical = normalize_skill(s)
        if canonical.lower() not in seen:
            seen.add(canonical.lower())
            result.append(canonical)
    return result


def get_related_skills(skill: str) -> list[str]:
    """Get related skills for a given skill."""
    skill_lower = skill.lower()
    for entry in SKILL_TAXONOMY:
        if entry["canonical"].lower() == skill_lower or skill_lower in [a.lower() for a in entry["aliases"]]:
            return entry["related"]
    return []


def get_skill_category(skill: str) -> str:
    """Get the category of a skill."""
    skill_lower = skill.lower()
    for entry in SKILL_TAXONOMY:
        if entry["canonical"].lower() == skill_lower or skill_lower in [a.lower() for a in entry["aliases"]]:
            return entry["category"]
    return "other"
