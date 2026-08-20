# Windows & Productivity Candidate Radar

**Review date:** 2026-08-20  
**Scope:** Public open-source Windows tools with immediate personal usefulness.  
**Status:** Research only — no software installed or copied into this repository.

## Summary

| Priority | Tool | Main use | License | Initial status |
|---:|---|---|---|---|
| 1 | [Microsoft PowerToys](https://github.com/microsoft/PowerToys) | Windows productivity toolkit | MIT | Reviewed candidate |
| 2 | [ShareX](https://github.com/ShareX/ShareX) | Screenshots, annotation, and recording | GPL-3.0 | Reviewed candidate |
| 3 | [LocalSend](https://github.com/localsend/localsend) | Private local file transfer between PC and phone | Apache-2.0 | Reviewed candidate |
| 4 | [PDF Arranger](https://github.com/pdfarranger/pdfarranger) | Merge, split, crop, rotate, and rearrange PDFs | GPL-3.0 | Candidate with limitations |
| 5 | [UniGetUI](https://github.com/Devolutions/UniGetUI) | Manage Windows software and updates | MIT | Candidate requiring caution |

## 1. Microsoft PowerToys

- **Problem solved:** Combines many small Windows improvements in one Microsoft-maintained package.
- **Relevant features:** PowerRename, Image Resizer, FancyZones, Always on Top, File Locksmith, Color Picker, Keyboard Manager, Command Palette, and File Explorer add-ons.
- **Maintenance:** Very active repository with frequent releases and a published security policy.
- **Permissions:** Runs in the background; some functions may request elevation or integrate with Windows Explorer and keyboard shortcuts.
- **Risks/limitations:** It is a large suite. Enabling every module adds unnecessary background features and shortcut conflicts.
- **Recommendation:** Strong candidate. Install only if at least two or three modules are useful, then disable the rest.
- **Suggested first modules:** PowerRename, Image Resizer, File Locksmith, FancyZones.

## 2. ShareX

- **Problem solved:** Faster screenshots, precise region capture, annotation, scrolling capture, screen recording, and repeatable capture workflows.
- **Maintenance:** Long-running, active Windows project with published releases and SHA-256 hashes for release assets.
- **Permissions:** Can read the screen and clipboard. It can also upload captures to external services when upload actions are configured.
- **Risks/limitations:** Accidental upload is the main privacy concern, especially for drawings, email, or work information.
- **Recommendation:** Strong personal-use candidate. Configure captures to save locally only and disable automatic upload actions before normal use.

## 3. LocalSend

- **Problem solved:** Transfers files and text directly between nearby devices over the local network without cloud storage.
- **Personal fit:** Useful for moving screenshots, PDFs, photos, and documents between the ASUS laptop and OnePlus phone.
- **Maintenance:** Active cross-platform project with signed recent release commits.
- **Permissions:** Requires local-network and firewall access; receiving devices can write incoming files.
- **Risks/limitations:** Use trusted-network and device-approval settings. Do not automatically accept files from unknown devices.
- **Recommendation:** Strong candidate if phone-to-PC transfers are currently inconvenient.

## 4. PDF Arranger

- **Problem solved:** Simple visual merging, splitting, rotating, cropping, and reordering of PDF pages.
- **Maintenance:** Established project with many releases.
- **Permissions:** Reads and rewrites local PDF files; no cloud connection is required for its normal purpose.
- **Risks/limitations:** The current project notes that Windows users should remain on the older Windows build 1.10.0 while source release 1.10.1 targets newer Python. A documented issue also warns that bookmarks/outlines may be lost in some save operations.
- **Recommendation:** Useful but test on copies. Do not use it first on an important drawing set containing bookmarks, signatures, forms, or advanced PDF metadata.

## 5. UniGetUI

- **Problem solved:** Provides a graphical interface for WinGet and other package managers to discover, install, update, and remove applications.
- **Maintenance:** Originally developed as WingetUI/UniGetUI and now maintained under Devolutions. The project remains open source.
- **Permissions:** Software installation and updates may require administrator access. It downloads and executes installers supplied through external package repositories.
- **Risks/limitations:** The repository explicitly warns about fake UniGetUI websites. Package quality still depends on each package source and publisher.
- **Recommendation:** Potentially useful later, but normal WinGet or Microsoft Store updates are simpler for the current laptop setup. Use only the official repository or Devolutions site.

## Initial recommendation

The best first trial is **PowerToys** if Windows productivity is the priority, or **LocalSend** if transferring files between phone and laptop is a regular annoyance.

**ShareX** is potentially the most useful for conversations and technical troubleshooting because it improves screenshot capture and annotation, but it should be configured for local-only storage before handling work material.

## Safe trial procedure

1. Choose one tool only.
2. Download it from the official repository release page or official Microsoft Store entry.
3. Verify the publisher and release asset.
4. Review requested permissions.
5. Disable unnecessary startup modules and online-upload features.
6. Test with disposable files.
7. Record the installed version, settings, and decision in this repository.

## Sources checked

- [Microsoft PowerToys repository](https://github.com/microsoft/PowerToys)
- [Microsoft PowerToys releases](https://github.com/microsoft/PowerToys/releases)
- [ShareX repository](https://github.com/ShareX/ShareX)
- [ShareX releases](https://github.com/ShareX/ShareX/releases)
- [LocalSend repository](https://github.com/localsend/localsend)
- [LocalSend releases](https://github.com/localsend/localsend/releases)
- [PDF Arranger repository](https://github.com/pdfarranger/pdfarranger)
- [PDF Arranger releases](https://github.com/pdfarranger/pdfarranger/releases)
- [UniGetUI repository](https://github.com/Devolutions/UniGetUI)
