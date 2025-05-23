### Home.py

### IMPORTS
### ________________________________________________________________
import random
import streamlit as st

from src.models_load import load_models
from src.utils import create_clickable_blog_post_with_image, blog_posts
from styles.styles import spacer
from src.tutorial_utils import ensure_tutorial_mockups


def main():
    st.set_page_config(
        page_title='BuddyGuard',
        page_icon='🕵️‍♂️',
        layout='wide',
        initial_sidebar_state='expanded',
        menu_items={ 'Get Help': None, 'Report a bug': None, 'About': None }
    )

    logo_path = "images/Buddyguard_4_3.png"
    st.html("""
      <style>
        [alt=Logo] {
          height: 10rem;
        }
      </style>
            """)

    st.logo(logo_path)

    st.markdown(
        r"""
        <style>
        .stDeployButton { visibility: hidden; }
        </style>
        """, unsafe_allow_html=True
    )

    # Load models on startup
    if 'models' not in st.session_state:
        with st.spinner("Loading AI models (this may take a minute)..."):
            st.session_state.models = load_models()
            # Generate mockup images for the tutorial if they don't exist
            ensure_tutorial_mockups()

    # Center the image
    st.markdown(
        """
        <style>
        .centered-image { display: block; margin-left: auto; margin-right: auto; width: 200px;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    text_content = """
        ## BuddyGuard: Keeping Online Adventures Safe and Fun.

        This Web application utilizes Machine Learning to detect harmful content in user generated videos by analyzing both the visual elements and spoken words.

        *Disclaimer: This application is designed for educational and research purposes.*
        """

    # Create two columns with a ratio (you can adjust the numbers)
    col1, col2 = st.columns([2, 1])  # col1 will be wider (for text)

    # Place the text in the left column
    with col1:
        st.text(" ")
        spacer(30)
        st.markdown(text_content)
        col1_1, col1_2 = st.columns(2)
        with col1_1:
            if st.button("Get Started", type="primary", use_container_width=True):
                st.switch_page("pages/1__Upload & Process.py")  # Direct page switch
        with col1_2:
            if st.button("Take Tutorial", use_container_width=True):
                st.switch_page("pages/4__Tutorial.py")  # Link to our new tutorial page

    # Center the image within the right column
    with col2:
        st.markdown(
            """
            <style>
            .centered-image { display: block; margin-left: auto; margin-right: auto; width: 200px;}
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.image("saves/Buddyguard_4_3.png", use_container_width=True)  # use_column_width for responsiveness

    st.write("---")

    # Blog posts section added to home_page
    st.subheader("Related Articles")

    # Randomly select 2 blog posts
    random_posts = random.sample(blog_posts, min(2, len(blog_posts)))

    # Display the randomly selected blog posts in rows of 2 (at most)
    if random_posts:
        if len(random_posts) == 1:
            create_clickable_blog_post_with_image(
                random_posts[0]["title"],
                random_posts[0]["url"],
                random_posts[0]["summary"],
                random_posts[0]["image_url"],
            )
        else:
            col1, col2 = st.columns(2)
            with col1:
                post1 = random_posts[0]
                create_clickable_blog_post_with_image(
                    post1["title"], post1["url"], post1["summary"], post1["image_url"]
                )
            with col2:
                post2 = random_posts[1]
                create_clickable_blog_post_with_image(
                    post2["title"], post2["url"], post2["summary"], post2["image_url"]
                )
    else:
        st.info("No blog posts available.")


if __name__ == '__main__':
    main()

### END
### ________________________________________________________________