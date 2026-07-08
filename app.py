import streamlit as st
import urllib.parse

# Page configuration
st.set_page_config(page_title="Discord Server Lookup", page_icon="🔍", layout="centered")

st.title("🔍 Discord Public Server Recon")
st.write("Analyze public footprints and search for historical indexing of specific servers.")

# Input section
search_type = s.radio("Lookup Method", ["Server Name", "Server ID"])
query = st.text_input(f"Enter {search_type}:")

if st.button("Run OSINT Search"):
    if not query:
        st.warning("Please enter a valid query.")
    else:
        st.subheader("Results & Footprint Links")
        
        # URL encode the query for safe searching
        encoded_query = urllib.parse.quote(query)
        
        st.info(f"Analyzing public spaces for: **{query}**")
        
        # Generate targeted search links to find cached invites
        st.write("### 🌐 Potential Public Sources")
        
        # Google Dorking for archived invites
        google_dork = f"https://www.google.com/search?q=site:discord.gg+{encoded_query}"
        st.markdown(f"- [Search Google for Indexed Invites]({google_dork})")
        
        # Top.gg lookup
        top_gg_search = f"https://top.gg/servers/search?q={encoded_query}"
        st.markdown(f"- [Check Top.gg Registry]({top_gg_search})")
        
        # Disboard lookup
        disboard_search = f"https://disboard.org/search?keyword={encoded_query}"
        st.markdown(f"- [Check Disboard Index]({disboard_search})")

        st.success("Search queries generated. If no active invites exist in these databases, the server is securely private.")
