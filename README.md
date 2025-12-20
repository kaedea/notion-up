# notion-up
[中文说明](https://www.kaedea.com/2021/10/01/devops/notion-backup/)

![](https://www.kaedea.com/assets/8f134329_a1a6_49b2_97a4_c07ea4c3e733_untitled.png)

NotionUp (Notion Backup) is a python repo helping you to backup notion data automatically.

## **Getting Started**

### **Prepare**

To get started with NotionUp, you should:

1. Prepare your Notion's username(email) and password, or just find your `notion_token_v2`.
2. Run `notion-up/main.py` with your configs.

Check [here](https://github.com/kaedea/notion-down/blob/master/dist/parse_readme/notiondown_gettokenv2.md) to find out your `notion_token_v2` if need. BTW, `file_token` can also be found here, and if you don't find file_token, you need to have at least had exported a file manually once.

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

NotionUp provides a GitHub Actions workflow to automate the backup process. Check `.github/workflows/notion-backup.yml` for details.

The workflow performs the following:
1.  **Export**: Downloads your Notion workspace as a HTML/Markdown ZIP.
2.  **Scrub**: Automatically removes sensitive `*Personals*` directories.
3.  **Flatten**: Unzips and flattens the directory structure for clean Git history.
4.  **LFS**: Supports Git LFS for large binary attachments (images, PDFs).
5.  **Release**: Creates a GitHub Release with the cleaned ZIP archive.

As examples, check the output at [Release](https://github.com/kaedea/notion-up/releases) and the [dist](https://github.com/kaedea/notion-up/tree/master/dist) directory.

### Backup Schedule

You can enable the cron job in the workflow file to run backups automatically (e.g., weekly).

```yaml
on:
  schedule:
    - cron: '0 22 * * 0' # Sundays at 22:00 UTC
```

### Run Modes
The workflow includes granular run modes:
- `real_backup`: Standard production run (Export -> Cleanup -> PR -> Release).
- `debug_exported_url`: Tests Notion API connectivity and export URL generation.
- `debug_unzipping`: Skip the slow export and test the processing logic using the latest release ZIP.

## **Showcase**

Integrated with GitHub Actions. See [.github/workflows/notion-backup.yml](.github/workflows/notion-backup.yml).
