import streamlit as st
from streamlit_app import VRPOptimizerApp


def main():
    """Initialize and run the Streamlit application."""
    app = VRPOptimizerApp()
    app.run()


if __name__ == "__main__":
    main()
