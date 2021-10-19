# NotionDown Custom Config

# NotionDown Custom Configurations

This page shows how to run NotionDown with custom args, and how to configure custom page properties.

## Basic Config

Run `notion-down/main.py` with args:

```bash
PYTHONPATH=./ python main.py \
    --blog_url <Notion Post Url> \
    --token_v2 <token_v2>
```

Run `notion-down/main.py` with config file:

```bash
xxx --config_file '.config_file.json'

# cat '.config_file.json'
{
  "debuggable": false,
  "channels": [
    "default"
  ],
  "page_titles": [
    "all"
  ],
  "token_v2": "xxx",
  "blog_url": "yyy"
}
```

Set `notion token` at SysEnv:

```bash
# Only token is supported to be configured at SysEnv.
export NOTION_TOKEN_V2=<your_token>
```

Your can configure notion-down args by cli-args, config_file or SysEnv parameters with the following override priority.

Priority: cli args > config_file > SysEnv parameters > NotionDown default

## Configure MD Files for HEXO Source

`WIP`

## Configure Output Text Inspections

### Chinese-English Concat Separation

Install `pangu` module to enable cn-en concat separation optimize.

```bash
pip install pangu
```

### Chinese Spelling Error Check

Add arg `channels` with "SpellInspect" config to enable SpellingError check.

```bash
xxx --channels xxx|yyy|SpellInspect
```

## NotionDown Arguments Description

For now, NotionDown support page properties as the following:

[Untitled](NotionDown%20Custom%20Config%203c21bc204f0b48c794ff86c6f38fe448/Untitled%20Database%205e7e3401a02a4f13bc291a22870ebaa7.csv)

## NotionDown Page Properties Config

NotionDown offers several custom properties to configure how markdown file generated.

For example, add a following `Plain Text` code block in your notion page to get your customization.

```
[notion-down-properties]
Title = NotionDown Custom Page Properties Support
Date = 2021-05-20
Published = false
Category = NotionDown
Tag = Notion, NotionDown
FileLocate =
FileName = notiondown_custom_configs
```

For now, NotionDown support page properties as the following:

[Untitled](NotionDown%20Custom%20Config%203c21bc204f0b48c794ff86c6f38fe448/Untitled%20Database%208818f00cbc684caaa89eb19ac003d4e6.csv)