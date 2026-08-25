# Run the first V0 interface

This is a local single-feeder interface for the Electrical Design Checker.

## Windows / PowerShell

From the `electrical-engineering/design-checker` folder:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Your browser should open the local app automatically. If it does not, use the local URL printed by Streamlit in the terminal.

## What this UI is for

- enter one feeder without editing Python
- see Ib, selected breaker In, supported cable Iz and voltage drop
- distinguish PASS / FAIL / NOT VERIFIED
- inspect calculation/source traces and unsupported conditions

## V0 limitations

The interface intentionally exposes the current engine limits rather than hiding them. The IEC 60364-5-52 dataset is narrow, fire-rated cable families are not automatically treated as generic XLPE, and current IEC 60364-4-43 protection verification is not yet implemented.
