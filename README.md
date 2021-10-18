# Notion Up

## Getting Started

### Prepare

To get started with NotionDown, you should:

1. Prepare `notion_token_v2`.
1. Run `notion-up/main.py` with your configs.

Check [here](https://github.com/kaedea/notion-down/blob/master/dist/parse_readme/notiondown_gettokenv2.md) to get `notion_token_v2`. 


### Run NotionUp

Basically just run `notion-down/main.py` :

```Bash
# Run with cli cmd
PYTHONPATH=./ python main.py --token_v2 <token_v2>

# or
PYTHONPATH=./ python main.py \
    --config_file '.config_file.json'

# Your can configure notion-down args by cli-args, config_file or SysEnv parameters
# Priority: cli args > config_file > SysEnv parameters > NotionDown default
```


## Showcase
WIP
