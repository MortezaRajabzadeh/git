# Python-GithubAccountCreator

This Python script automates the creation of GitHub accounts using [mail.tm](https://mail.tm/en/)'s API. It handles the entire signup with minimal human intervention for the manual captcha solving.

It contains logic to simulate 'human-like' input typing and delays to minimize detection by GitHub's anti-bot measures.
It also uses 'undetected_geckodriver' which is based on selenium's webdriver to stay in stealth mode ;)

To end the script at any point in time, just press the middle mouse button or Ctrl+C in the terminal.

## Features

- **Automated Account Creation**: Creates GitHub accounts with random usernames
- **Temporary Email Integration**: Uses mail.tm API for disposable email addresses
- **Manual Puzzle Support**: Pauses for manual completion of visual puzzles
- **Email Verification**: Automatically retrieves and enters verification codes
- **Account Logging**: Saves all account details to a text file
- **Continuous Operation**: Can create multiple accounts in sequence

## Prerequisites

1. **Python 3.7+** installed on your system
2. **Firefox browser** installed
4. **Internet connection** for API calls and web automation

## Installation

1. Clone or download this repository
2. Navigate to the project directory
3. Run the setup script:

```bash
chmod +x setup.sh
./setup.sh
```

Or install manually:

```bash
pip install -r requirements.txt
```

## Configuration

### Default Settings
- **Password**: `Testpass@123` (used for all accounts)
- **Username**: Random generation (format: `user` + 8 random characters)
- **Email**: Temporary emails from mail.tm
- **Output File**: `github_accounts.txt`

## Usage

### Basic Usage

```bash
source venv/bin/activate
python main.py
        or
python3 main.py
```

The script will prompt you for the number of accounts to create (or unlimited).

### Manual Intervention Points

The script requires manual intervention at:

- **Visual Puzzle**: When GitHub shows a visual puzzle (CAPTCHA), you'll see:
   ```
   MANUAL ACTION REQUIRED!
   Please complete the visual puzzle in the browser.
   Once you reach the 'Enter code sent to your email' screen,
   Bring your mouse to bottom right of the screen to continue...
   ```

### Account Creation Flow

1. **Create temporary email** using mail.tm API
2. **Navigate to GitHub signup** page
3. **Fill signup form** with generated details
4. **Handle email conflicts** by creating new temp email if needed
5. **Wait for manual puzzle completion** by user
6. **Retrieve verification code** from temp email
7. **Enter verification code** on GitHub
8. **Complete signup process** and skip optional steps
9. **Signs you in** with the created account
10. **Save account details** to file
11. **Repeat** for next account

## Output

Account details are saved to `github_accounts.txt` in JSON format:

```json
{"email": "temp123@mail.tm", "username": "user7a9b2c1d", "password": "Testpass@123", "temp_email_password": "temppassword123", "created_at": "2024-01-15 14:30:22"}
```

## Troubleshooting

### Common Issues

1. **Firefox not starting**
   - Check Firefox installation
   - Verify geckodriver compatibility

2. **Email creation fails**
   - Check internet connection
   - mail.tm service might be temporarily down

3. **Verification code not found**
   - Email might take longer to arrive
   - Check spam folder manually

### Browser Visibility

The script runs with visible browser windows to allow manual intervention. If you want to run headless (not recommended due to manual steps), uncomment the headless option in the code:

```python
options.add_argument("--headless")
```

## Security Considerations

- **Password Security**: The default password is visible in the code. Consider using environment variables for production use.
- **Account Storage**: Account details are stored in plain text. Consider encryption for sensitive data.
- **Rate Limiting**: GitHub may implement rate limiting. The script includes delays to avoid detection.

## Legal Notice

This script is for educational purposes only. Users are responsible for:
- Complying with GitHub's Terms of Service
- Complying with mail.tm's Terms of Service
- Using created accounts responsibly
- Not violating any applicable laws or regulations

## Customization

### Changing Password

Edit the password in the script:

```python
def __init__(self):
    self.password = "YourNewPassword123!"
```

### Modifying Username Generation

Customize the username generation logic:

```python
def generate_random_username(self, length=8):
    # Your custom logic here
    return f"custom{username}"
```

### Adjusting Timeouts

Modify wait times for slower connections:

```python
self.wait = WebDriverWait(self.driver, 60)  # Increase timeout
```

## Dependencies

- `selenium` - Web automation
- `requests` - HTTP requests for mail.tm API
- `undetected_geckodriver` - Firefox WebDriver
- `pynput` - To check for mouse and inputs and cursor placement on screen
- `screeninfo` - To get information about the screen, like resolution

## Found a bug ? / Have an issue ? :-
  📧 shivamchaudharymay2006@gmail.com

## Disclaimer

This tool is provided as-is without warranty. Users assume all responsibility for its use and any consequences thereof.
