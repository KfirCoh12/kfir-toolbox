# Adding and Reviewing Tools

Use this checklist before adopting a third-party project or adding a custom utility.

## Candidate record

- **Tool name:**
- **Problem it solves:**
- **Original repository:**
- **License:**
- **Version or commit reviewed:**
- **Category:**
- **Status:** Candidate
- **Expected users:**
- **Required software:**
- **Required permissions:**

## Review checklist

- [ ] The source repository and author are identifiable.
- [ ] The license allows the intended use and modification.
- [ ] Recent releases, commits, issues, and maintenance status were checked.
- [ ] Compatibility with the intended software version was confirmed.
- [ ] Dependencies and installation steps were reviewed.
- [ ] Network access, file access, telemetry, and external communication were checked.
- [ ] No credentials, confidential data, or unsafe defaults are included.
- [ ] The tool was tested on disposable sample data.
- [ ] Limitations and rollback or uninstall steps are documented.
- [ ] The decision to approve, reject, or archive is recorded.

## Change workflow

1. Create a dedicated branch.
2. Add or modify one tool with its documentation.
3. Test it with safe sample data.
4. Open a pull request explaining the purpose, tests, and risks.
5. Review the changes before merging into `main`.

## Third-party code

Do not copy third-party code without preserving required attribution and license information. When practical, prefer linking to or forking the original repository and keep local modifications clearly documented.
