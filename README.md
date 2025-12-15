# notion-up
[中文说明](https://www.kaedea.com/2021/10/01/devops/notion-backup/)

![](https://www.kaedea.com/assets/8f134329_a1a6_49b2_97a4_c07ea4c3e733_untitled.png)

NotionUp (Notion Backup) is a python repo helping you to backup notion data automatically.

## **Getting Started**

### **Prepare**

To get started with NotionUp, you should:

1. Prepare your Notion's username(email) and password, or just find your `notion_token_v2`.
2. Run `notion-up/main.py` with your configs.

Check [here](https://github.com/kaedea/notion-down/blob/master/dist/parse_readme/notiondown_gettokenv2.md) to find out your `notion_token_v2` if need.

### **Run CLI**

Basically just run `notion-down/main.py` :

```bash
# Run with cli cmd
PYTHONPATH=./ python main.py
    --token_v2 <token_v2>
    --username <username>  # Only when token_v2 is not presented
    --password <password>  # Only when token_v2 is not presented

# or
PYTHONPATH=./ python main.py \
    --config_file '.config_file.json'

# Your can configure notion-down args by cli-args, config_file or SysEnv parameters
# Priority: cli args > config_file > SysEnv parameters > NotionDown default
```

### Archive to GitHub Release

Check the following workflows and jobs in `.circleci/config.yml` to get how it works.

```yaml
workflows:
  backup-notion:
    jobs:
      - export-workspace
      - publish-github-release:
          requires:
            - export-workspace
```

As examples, check the output at [Release](https://github.com/kaedea/notion-up/releases) and [notion-exported](https://github.com/kaedea/notion-up/tree/master/dist).

### Backup nightly

Check the following crontab workflows.

```yaml
workflows:
  backup-notion-nightly:
    triggers:
      - schedule:
          cron: "0 * * * *"  # every hour
          filters:
            branches:
              only:
                - master
    jobs:
      - export-workspace
      - publish-github-release:
          requires:
            - export-workspace
```

## **Showcase**

Work with CircleCI, see `.circleci/config.yml`.
