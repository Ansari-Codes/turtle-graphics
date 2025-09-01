from nicegui import ui

with ui.card():
    ui.label("Custom Emoji Picker:")
    emoji_output = ui.label("Selected: ")

    # Load the UMD build instead of the ESM build
    ui.add_head_html('''
    <script src="https://cdn.jsdelivr.net/npm/@joeattardi/emoji-button@4.6.4/dist/umd/emoji-button.min.js"></script>
    ''')

    # Button with stable ID
    picker_btn = ui.button('Pick Emoji')
    picker_btn._props['id'] = 'emoji-btn'

    # JS handler: toggle emoji picker
    js_code = """
    const button = document.querySelector('#emoji-btn');
    if (!window.myEmojiPicker) {
        window.myEmojiPicker = new EmojiButton.EmojiButton();
        window.myEmojiPicker.on('emoji', selection => {
            const ev = new CustomEvent("emoji_selected", {detail: selection.emoji});
            document.dispatchEvent(ev);
        });
    }
    window.myEmojiPicker.togglePicker(button);
    """
    picker_btn.on('click', js_handler=js_code)

    # Python-side listener
    def on_emoji(e):
        emoji_output.set_text(f"Selected: {e.args}")

    ui.on('emoji_selected', on_emoji)

ui.run(port=9000)
