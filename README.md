# SYNAPSE — Explore the Human Brain

Created by Saksham Singh Chowhan. App version 0.14.1.

An interactive educational platform with twelve brain-region lessons, controlled
experiments, spiking-neuron recordings and a 100-cell movement microscope.
The models simplify selected computations; they do not reproduce a human brain
or measure the visitor's brain activity. Each lesson explains its scope.

## Publish with Streamlit Community Cloud

1. Create a public GitHub repository, for example SYNAPSE-Brain-Learning.
2. Upload the CONTENTS of this folder to the repository root. streamlit_app.py,
   requirements.txt, synapse/, ui_assets/ and .streamlit/config.toml must keep
   their relative paths. Upload extracted files, not the ZIP itself.
3. At https://share.streamlit.io/ create an app from that repository.
4. Use branch main, entrypoint streamlit_app.py, and Python 3.12 in Advanced settings.
5. Choose an available app subdomain and deploy. Make app sharing public if needed.

No API key, Ollama, database or paid model service is needed for this app.
The requirements.txt in this deployment package contains UI dependencies as well
as the numerical dependencies; Community Cloud discovers that filename directly.

## Run this deployment folder locally

python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py

## State and visitors

Experiment state belongs to the visitor's Streamlit session. Download the
notebook, experiment bundle or relevant model checkpoint to keep work across
session loss or a server restart. This package does not add accounts or a
shared cloud database. Visitors can run computation on the hosting service;
heavy concurrent training may reach Community Cloud resource limits.

## Assets

Keep ui_assets/anatomy/CREDITS.md and SOURCES.json with the distributed medical
illustrations. Their authorship, source links and licences are recorded there.

## Deployment references

https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies
