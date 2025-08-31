from nicegui import ui

@ui.page('/')
async def _():
    with ui.card():
        ui.label("Emoji Picker:")
        emoji_output = ui.label("Selected: ")

        ui.add_head_html('''
        <script src="https://cdn.jsdelivr.net/npm/emoji-mart@5.4.0/dist/browser.js"></script>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/emoji-mart@5.4.0/dist/browser.css"/>
        <style>.emoji-picker { max-width: 350px; }</style>
        ''')

        picker = ui.html('''
        <div id="picker" class="emoji-picker"></div>
        ''')
        await ui.run_javascript("""
            <script>
        const picker = new EmojiMart.Picker({ onEmojiSelect: e => {
            const ev = new CustomEvent("emoji_selected", {detail: e.native});
            document.dispatchEvent(ev);
        }});
        document.getElementById("picker").appendChild(picker);
        </script>
        """, timeout=100)
        def on_emoji(e):
            emoji_output.set_text(f"Selected: {e.args}")

        ui.on('emoji_selected', on_emoji)

ui.run(port=8000)
