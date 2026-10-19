"""A small offline Streamlit component for the twelve experiential activities."""

import streamlit as st
import streamlit.components.v1 as components

from .experience_lab import ASSETS, ACTIVITIES, ExperienceSession
from .region_content import ATLAS
from .region_view import asset_uri

_component=components.declare_component('synapse_experience',path=str(ASSETS))


def init():
    if 'experience_session' not in st.session_state: st.session_state.experience_session=ExperienceSession()


def page(id):
    init();session=st.session_state.experience_session
    focus=ATLAS[id];view=focus['view']
    filename={'lateral':'brain_regions.png','medial':'brain_medial.png','hippocampus':'hippocampus.png','deep':'brain_section.png'}[view]
    value=_component(lesson=id,config=ACTIVITIES[id],state=session.states.get(id),epoch=session.epoch,
        last_sequence=session.sequences.get(id,0),reply=session.replies.get(id),image=asset_uri(filename),focus=focus,
        orientation='Anterior at left' if view=='hippocampus' else 'Coronal view' if view=='deep' else 'Anterior at right',
        key='experience_'+id,default=None)
    try:
        if session.handle(value,id): st.rerun()
    except ValueError as exc: st.error(str(exc))
