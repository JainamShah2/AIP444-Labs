# test_tool.py
from tools import read_github_files

def test():
    print("Testing read_github_files...\n")

    content = read_github_files({
      "files": [
        {
            "owner": "microsoft",
            "repo": "vscode",
            "path": "package.json",
            "ref": "main",
            "start_line": 1,
            "max_lines": 500,
        }
      ]
    })

    print(content)

if __name__ == "__main__":
    test()