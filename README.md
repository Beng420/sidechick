# sidechick
A collection of useful tools for me and my friends

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start Sidechick:

```bash
python sidechick.pyw
```

Sidechick uses a Python backend with a HTML/CSS/JS desktop UI through pywebview.

Sidechick can check GitHub Releases for updates. It will show an Update button when a newer release is available. Updates replace program files only; your local script configs stay on your machine.

Multiple scripts can run at the same time. Runtime controls in Sidechick can pause/resume scripts and adjust supported modes without restarting them.

Configs are stored per script:

- `configs/fih.json`
- `configs/superpairs.json`
- `configs/sidechick.json`

Included scripts:

- `fih.py`: fishing helper
- `superpairs.py`: Superpairs helper
