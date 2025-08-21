from nicegui import ui, app
import re, random, asyncio
import aiosmtplib
from email.message import EmailMessage
import asyncpg, bcrypt
from contextlib import asynccontextmanager
from db import get_db_conn
from datetime import datetime

# -- Config --
email_sender = 'ansaricodes@gmail.com'
email_password = 'bsrx rkmc rjhb utxl'
DB_CONFIG = {
    'user': 'postgres',
    'password': 'postgres@app',
    'database': 'users',
    'host': 'localhost',
    'port': 7864,
}

@asynccontextmanager
async def disable(button: ui.button):
    button.set_enabled(False)
    button.update()
    await asyncio.sleep(0.05)
    try:
        button.set_enabled(False)
        button.update()
        yield
    finally:
        button.set_enabled(True)
        button.update()
        await asyncio.sleep(0.05)  # Ensure UI update after re-enabling

async def user_exists(username: str, mail: str):
    conn = await get_db_conn()
    try:
        result = await conn.fetchrow(
            'SELECT * FROM accounts WHERE username=$1 OR mail=$2',
            username, mail
        )
    finally:
        await conn.close()
        await asyncio.sleep(0.1)  # Brief delay before dismissing
    exists = result is not None
    msg = "Username or email already exists!" if exists else ""
    type_ = "negative" if exists else "positive"
    return msg, type_, exists

async def add_user(username: str, mail: str, pswd: str):
    conn = await get_db_conn()
    try:
        pswd_hashed = bcrypt.hashpw(pswd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        async with conn.transaction():
            await conn.fetchrow(
                'INSERT INTO accounts (username, mail, pswd) VALUES ($1, $2, $3) RETURNING id',
                username, mail, pswd_hashed
            )
        await asyncio.sleep(0.1)  # Ensure UI updates after dismissal
        return "Account created successfully!", "positive", True
    except asyncpg.UniqueViolationError:
        await asyncio.sleep(0.1)  # Ensure UI updates after dismissal
        return "Username or Email already exists!", "negative", False
    except Exception as e:
        await asyncio.sleep(0.1)  # Ensure UI updates after dismissal
        return f"Failed to save user: {e}", "negative", False
    finally:
        await conn.close()

async def send_code_email(to_email: str, code: int, theme):
    subject = '🔐 Your Signup Verification Code'
    html_body = f"""
<html>
  <body style="margin:0; padding:0; font-family: 'Segoe UI', Roboto, sans-serif; background-color: #f4f4f4; color: #333;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td align="center" style="padding: 40px 10px;">
          <table width="600" cellpadding="0" cellspacing="0" style="background: #ffffff; border-radius: 10px; padding: 40px; box-shadow: 0 2px 12px rgba(0,0,0,0.08);">
            <tr>
              <td align="center" style="font-size: 24px; font-weight: 600; color: {theme['primary']}; padding-bottom: 20px;">
                Confirm your email address
              </td>
            </tr>
            <tr>
              <td style="font-size: 16px; padding-bottom: 20px;">
                Hi there,<br><br>
                To complete your signup, please enter the verification code below in the app:
              </td>
            </tr>
            <tr>
              <td align="center" style="padding: 20px 0;">
                <div style="
                  display: inline-block;
                  font-size: 30px;
                  font-weight: bold;
                  letter-spacing: 6px;
                  background: #f0f8ff;
                  color: {theme['primary']};
                  padding: 16px 36px;
                  border-radius: 8px;
                  border: 1px solid {theme['primary']};
                  user-select: text;
                ">
                  {code}
                </div>
              </td>
            </tr>
            <tr>
              <td style="font-size: 14px; color: #555; padding-top: 10px;">
                If you didn’t request this, you can safely ignore this email.
              </td>
            </tr>
            <tr>
              <td style="padding-top: 40px; font-size: 12px; color: #aaa; text-align: center;">
                &copy; {datetime.now().year} Turtle Graphics. All rights reserved.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
    """
    msg = EmailMessage()
    msg['From'] = email_sender
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.set_content(f'Your code: {code}')
    msg.add_alternative(html_body, subtype='html')
    try:
        await aiosmtplib.send(
            msg,
            hostname="smtp.gmail.com",
            port=465,
            username=email_sender,
            password=email_password,
            use_tls=True
        )
        print(f"📨 Code sent to {to_email}")
        return "Code sent successfully!", "positive", True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return "Failed to send code. Try again later.", "negative", True

# -- Password Helpers --
def password_check(pswd):
    return {
        '8 characters': len(pswd) >= 8,
        'UPPER & lower case': bool(re.search(r'(?=.*[a-z])(?=.*[A-Z])', pswd)),
        'Symbol': bool(re.search(r'[\W_]', pswd)),
        '1 number': len(re.findall(r'\d', pswd)) >= 1,
    }

def password_strength_color(score):
    colors = ['#f44336', '#ff9800', '#cddc39', '#8bc34a', '#4caf50']
    return colors[min(score, len(colors)-1)]

# -- UI --
def create_signup(theme, btn, props, propsinp, style_inp):
    ui.colors(**theme)    
    real_code = random.randint(99999, 999999)
    print(real_code)
    dark = app.storage.user.get('theme_dark')
    ui.dark_mode(dark)
    with ui.column().classes('w-full h-[95vh] items-center'):
        ui.element('div').style('height: 1vh')
        ui.image('data/banner.png').classes('w-[300px]').style('user-select: none;')
        with ui.stepper() as stepper:
            with ui.step('Account'):
                username = ui.input('Username').props(propsinp).classes('w-full').classes(style_inp)
                user_lbl = ui.label()
                mail = ui.input('Email').props(propsinp).classes('w-full').classes(style_inp)
                pswd = ui.input('Password', password=True, password_toggle_button=True).props(propsinp).classes('w-full').classes(style_inp)
                strength_bar = ui.linear_progress(value=0.0, show_value=False).classes('w-full mt-[-10px] mb-2')
                ui.label('Tip💡: Use numbers, upper & lower case letters and symbols')
                def on_pswd_change(e):
                    checks = password_check(e.value or "")
                    passed = sum(checks.values())
                    strength_bar.value = passed / 4
                    strength_bar.props(f'color={password_strength_color(passed)}')
                pswd.on_value_change(on_pswd_change)
                con = ui.button('Continue').props(props).style(btn).classes('w-full mt-4')
                async def _(e):
                  checks = password_check(pswd.value or "")
                  passed = sum(checks.values())
                  if passed >= 3 and username.value and mail.value:
                      msg, type_, exists = await user_exists(username.value, mail.value)
                      if exists:
                          user_lbl.style('color:red;').set_text(msg)
                          e.sender.set_text("Exists!")
                          e.sender.update()
                          ui.notify(msg, type=type_)
                          return
                      msg, type_, sent = await send_code_email(mail.value, real_code, theme)
                      ui.notify(msg, type=type_)
                      if sent:
                          await asyncio.sleep(0.1)  # Brief delay before stepper advance
                          stepper.next()
                  else:
                      ui.notify("Please fill all the fields!", type="negative")
                con.on('click', _)
            with ui.step('Verification'):
                ui.label('Verify your Account').classes('text-xl font-bold text-center mb-4')
                code_input = ui.input('Enter verification code').props(propsinp).classes('w-full').classes(style_inp)
                async def submit_final():
                    if not code_input.value:
                        ui.notify('Please enter the verification code ❗', type="negative")
                        return
                    try:
                        if int(code_input.value) != real_code:
                            ui.notify("Invalid verification code!", type="negative")
                            return
                        msg, type_, success = await add_user(username.value, mail.value, pswd.value)
                        ui.notify(msg, type=type_)
                        if success:
                            ui.navigate.to('/login')
                    except ValueError:
                        ui.notify("Please enter a valid number for the verification code!", type="negative")
                ui.button("Create Account", on_click=submit_final).props(props).style(btn).classes('w-full mt-4')