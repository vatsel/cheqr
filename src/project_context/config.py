class DevConfig:
    ANTHROPIC_API_KEY_LOCAL_PATH = "secrets/Anthropic-key"
    API_SECRET_VAR_NAME = "APPS_SCRIPT_SECRET"
    SUPABASE_PASS_VAR_NAME = "SUPABASE_DB_PASS"
    LOCAL_SECRETS_PATH = "secrets/.env"
    PROMPT_PARSE_EMAIL = "src/project_context/ai/prompts/parse_email.txt"
    STORAGE_KEY_VAR_NAME = "STORAGE_KEY"
    
    MAX_TOKENS_IN_RESPONSE = 4000

    LOG_DIR = "logs"

    G_SECRET_API_ACCESS_NAME = "apps-script-secret"
    G_SECRET_ANTHROPIC_NAME = "anthropic-key-secret"
    G_SECRET_STORAGE_ENCRYPT_NAME = "strorage-key"
    G_SECRET_SUPABASE_CONN_URL = "supabase-conn-url"
    
    FREE_TRIAL_DAYS = 7

    LOCAL_DATASTORE_PROJECT_NAME = "local-test"

    TEMPLATES_DIR = "templates"
