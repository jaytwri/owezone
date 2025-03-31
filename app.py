from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a strong, random secret key

# Hardcoded users with hashed passwords
users = {
    "Jay": generate_password_hash("masterofthefuture"),
    "Yash": generate_password_hash("securepass"),
    "Pari": generate_password_hash("mypassword"),
    "Aaryan": generate_password_hash("letmein"),
    "Arjun": generate_password_hash("pass1234"),
    "Krishna": generate_password_hash("gameon")
}

# Allowed players list
allowed_players = {"Jay", "Yash", "Pari", "Aaryan", "Arjun", "Krishna"}

# Initialize database
def init_db():
    conn = sqlite3.connect('tournament.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    player1 TEXT,
                    player2 TEXT,
                    player3 TEXT,
                    player4 TEXT,
                    player5 TEXT,
                    player6 TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS balances (
                    player TEXT PRIMARY KEY,
                    balance INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS debts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    debtor TEXT,
                    creditor TEXT,
                    amount INTEGER)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users and check_password_hash(users[username], password):
            session['user'] = username
            return redirect(url_for('index'))
        else:
            return "Invalid username or password", 403
    
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/rankings')
def rankings():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    if "user" not in session:
        return redirect(url_for("login"))

    if session['user'] != "Jay":  # Restrict updates to Jay only
        return "You are not authorized to submit results.", 403

    date = request.form['date']
    players = [request.form.get(f'player{i}') for i in range(1, 7) if request.form.get(f'player{i}')]
    num_players = len(players)

    # Validate that all players are from the allowed list
    if not all(player in allowed_players for player in players):
        return "Invalid player name entered", 400

    conn = sqlite3.connect('tournament.db')
    c = conn.cursor()
    placeholders = ', '.join(['?'] * num_players)
    columns = ', '.join(f'player{i+1}' for i in range(num_players))

    query = f"INSERT INTO results (date, {columns}) VALUES (?, {placeholders})"

    c.execute(query, (date, *players[:num_players]))

    # c.execute(f"INSERT INTO results (date, {', '.join(f'player{i+1}' for i in range(num_players))}) VALUES (?, {', '.join(['?'] * num_players)})", 
    #           (date, *players))
    
    
    transactions = []
    if num_players == 6:
        transactions = [(players[5], players[0], 300), (players[4], players[1], 200), (players[3], players[2], 100)]
    elif num_players == 5:
        transactions = [(players[4], players[0], 300), (players[3], players[1], 200)]
    elif num_players == 4:
        transactions = [(players[3], players[0], 300), (players[2], players[1], 200)]
    elif num_players == 3:
        transactions = [(players[2], players[0], 300)]
    elif num_players == 2:
        transactions = [(players[1], players[0], 300)]
    
    for debtor, creditor, amount in transactions:
        c.execute("INSERT INTO debts (date, debtor, creditor, amount) VALUES (?, ?, ?, ?)", (date, debtor, creditor, amount))
        c.execute("INSERT INTO balances (player, balance) VALUES (?, 0) ON CONFLICT(player) DO NOTHING", (debtor,))
        c.execute("INSERT INTO balances (player, balance) VALUES (?, 0) ON CONFLICT(player) DO NOTHING", (creditor,))
        c.execute("UPDATE balances SET balance = balance - ? WHERE player = ?", (amount, debtor))
        c.execute("UPDATE balances SET balance = balance + ? WHERE player = ?", (amount, creditor))
    
    conn.commit()
    conn.close()
    return redirect(url_for('balances'))

@app.route('/balances')
def balances():
    if "user" not in session:
        return redirect(url_for("login"))
    
    conn = sqlite3.connect('tournament.db')
    c = conn.cursor()
    c.execute("SELECT * FROM balances")
    balances = c.fetchall()
    c.execute("SELECT debtor, creditor, SUM(amount) FROM debts GROUP BY debtor, creditor")
    debts = c.fetchall()
    conn.close()
    return render_template('balances.html', balances=balances, debts=debts)

@app.route('/reset', methods=['POST'])
def reset():
    if "user" not in session:
        return redirect(url_for("login"))
    if session['user'] != "Jay":
        return "You are not authorized to reset the tournament.", 403
    conn = sqlite3.connect('tournament.db')
    c = conn.cursor()
    c.execute("DELETE FROM results")
    c.execute("DELETE FROM balances")
    c.execute("DELETE FROM debts")
    conn.commit()
    conn.close()
    return redirect(url_for('balances'))

if __name__ == '__main__':
    app.run(debug=True)