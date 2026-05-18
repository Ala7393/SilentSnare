from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db
from decorators import login_required

bp = Blueprint('admin', __name__)

@bp.route('/')
@login_required
def index():
    return render_template('admin.html')

@bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    old_password = request.form['old_password']
    new_username = request.form['new_username']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    if new_password != confirm_password:
        flash('كلمة المرور الجديدة غير متطابقة', 'danger')
        return redirect(url_for('admin.index'))

    user_id = session['user_id']

    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user or not check_password_hash(user['password_hash'], old_password):
            flash('كلمة المرور القديمة غير صحيحة', 'danger')
            return redirect(url_for('admin.index'))

        hashed_new = generate_password_hash(new_password)
        db.execute(
            "UPDATE users SET username = ?, password_hash = ? WHERE id = ?",
            (new_username, hashed_new, user_id)
        )
        session['username'] = new_username
        flash('تم تحديث بيانات الدخول بنجاح', 'success')

    return redirect(url_for('admin.index'))
