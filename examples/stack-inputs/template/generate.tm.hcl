# MIT License, Copyright (c) 2026 Tevinch
generate_file "settings.json" {
  content = tm_jsonencode({
    stack       = terramate.stack.name
    region      = global.region
    account     = global.account
    environment = global.environment
  })
}
