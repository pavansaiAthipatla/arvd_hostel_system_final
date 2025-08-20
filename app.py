from flask import Flask, render_template, request, redirect, url_for, send_file, session
import os, csv, zipfile
from datetime import datetime
import qrcode

app = Flask(__name__)
app.secret_key = 'your_secret_key'

ATT_FILE = 'attendance.csv'
STUD_FILE = 'students.csv'
QR_FOLDER = 'qr_codes'
REPORTS = 'reports'
os.makedirs(QR_FOLDER, exist_ok=True)
os.makedirs(REPORTS, exist_ok=True)

def get_session(dt):
    h = dt.hour
    return 'Morning' if h<12 else 'Afternoon' if h<17 else 'Evening'

@app.route('/')
def index():
    return render_template('index.html')
from flask import jsonify  # Make sure it's imported at the top

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    data = request.get_json()
    student_id = data.get('student_id')

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    session_time = get_session(now)

    # Save attendance to CSV
    with open(ATT_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([student_id, timestamp, session_time])

    return jsonify({'status': 'success', 'scanned_id': student_id})

@app.route('/dashboard')
def dashboard():
    rec = []
    if os.path.exists(ATT_FILE):
        with open(ATT_FILE) as f:
            data = list(csv.reader(f))
        rec = data[-30:]
    return render_template('dashboard.html', records=rec)



@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        if request.form['username']=='arvdhostel' and request.form['password']=='hostel@2025':
            session['admin']=True
            return redirect('/admin')
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html', error=None)

@app.route('/admin', methods=['GET','POST'])
def admin():
    if not session.get('admin'):
        return redirect('/login')
    import json
    if request.method=='POST':
        sid = request.form['student_id']
        name = request.form['student_name']
        with open(STUD_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([sid, name])
        img = qrcode.make(f"{sid}_{name}")
        path = os.path.join(QR_FOLDER, f"{sid}.png")
        img.save(path)
    return render_template('admin.html')

@app.route('/download_qr_zip')
def download_qr_zip():
    zipf = zipfile.ZipFile('qr_codes.zip', 'w')
    for fn in os.listdir(QR_FOLDER):
        zipf.write(os.path.join(QR_FOLDER, fn), fn)
    zipf.close()
    return send_file('qr_codes.zip', as_attachment=True)

@app.route('/export_registered_students')
def export_students():
    return send_file(STUD_FILE, as_attachment=True)

@app.route('/view_attendance', methods=['GET'])
def view_attendance():
    if not session.get('admin'):
        return redirect('/login')
    s = request.args.get('start_date')
    e = request.args.get('end_date')
    sess = request.args.get('session')
    rows=[]
    if os.path.exists(ATT_FILE):
        with open(ATT_FILE) as f:
            for r in csv.reader(f):
                if s <= r[1].split()[0] <= e and (sess=='' or r[2]==sess):
                    rows.append(r)
    return render_template('admin.html', filtered=rows)

@app.route('/export_attendance', methods=['GET'])
def export_attendance():
    if not session.get('admin'):
        return redirect('/login')
    date = request.args['export_date']
    rng = request.args['range']
    filename = os.path.join(REPORTS, f"{rng}_{date}.csv")
    with open(ATT_FILE) as infile, open(filename,'w', newline='') as outfile:
        writer = csv.writer(outfile)
        for r in csv.reader(infile):
            if (rng=='daily' and r[1].startswith(date)) or \
               (rng=='weekly' and datetime.strptime(r[1],'%Y-%m-%d %H:%M:%S').isocalendar()[1]==datetime.strptime(date,'%Y-%m-%d').isocalendar()[1]) or \
               (rng=='monthly' and r[1][5:7]==date[5:7]):
                writer.writerow(r)
    return send_file(filename, as_attachment=True)
@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')

if __name__ == '__main__':
    open(ATT_FILE, 'a').close()
    open(STUD_FILE, 'a').close()
    app.run(debug=True)
