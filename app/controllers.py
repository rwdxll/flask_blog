# -*- coding: utf-8 -*-
from flask import render_template
from flask import request
from flask import session
from flask import redirect
from flask import url_for
from datetime import timedelta
from models import User, Post
from app import app
from app import db
import datetime


@app.before_request
def make_session_timeout():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=5)


@app.route('/')
@app.route('/index')
def index():
    try:
        posts = Post.query.order_by('id desc').all()[:5]
    except IndexError:
        posts = Post.query.order_by('id desc').all()
    users = []
    for post in posts:
        users.append(User.query.get(post.user_id))
    return render_template('index.html',
                           title='Flask',
                           posts=posts,
                           users=users)


@app.route('/login')
def login():
    if 'logged_in' in session:
        if session['logged_in']:
            return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/login_process', methods=['POST'])
def login_process():
    if request.method == 'POST':
        user_email = request.form['user_email']
        user_password = request.form['user_password']
        u = User.query.filter_by(email=user_email).first()
        if u is not None:
            if u.check_password_hash(password=user_password):
                session['user_name'] = user_email
                session['user_nickname'] = u.nickname
                session['logged_in'] = True
                if u.is_admin:
                    session['is_admin'] = True
        return redirect(url_for('index'))


@app.route('/join')
def join():
    if 'user_name' in session:
        if 'logged_in' in session and session['logged_in']:
            return redirect('index')
    return render_template('join.html')


@app.route('/join_process', methods=['POST'])
def join_process():
    if request.method == 'POST':
        new_user = User()
        new_user.email = request.form['user_email']
        new_user.nickname = request.form['user_nickname']
        new_user.set_password(request.form['user_password'])
        new_user.is_admin = False
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session['logged_in'] = False
    session.pop('is_admin', None)
    session.pop('user_name', None)
    session.pop('user_nickname', None)
    return redirect(url_for('index'))


@app.route('/write')
def write_post():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    return render_template('write.html')


@app.route('/write_process', methods=['POST'])
def write_process():
    if not session['logged_in']:
        return redirect(url_for('index'))
    u = User.query.filter_by(email=session['user_name']).first()
    p = Post()
    p.title = request.form['post_title']
    p.body = request.form['post_body']
    p.timestamp = datetime.datetime.utcnow()
    p.user_id = u.id
    db.session.add(p)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/posts/<int:post_id>')
def view_post(post_id):
    p = Post.query.get(post_id)
    return render_template('post_detail.html',
                           post=p)


@app.route('/edit_post/<int:post_id>')
def edit_post(post_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(email=session['user_name']).first()
    post = Post.query.get(post_id)
    if post.user_id != user.id:
        return redirect(url_for('index'))
    return render_template('edit_post.html',
                           post=post)


@app.route('/edit_process/<int:post_id>', methods=['POST'])
def edit_post_process(post_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(email=session['user_name']).first()
    post = Post.query.get(post_id)
    if post.user_id != user.id:
        return redirect(url_for('index'))
    post.title = request.form['post_title']
    post.body = request.form['post_body']
    db.session.commit()
    return redirect(url_for('view_my_post'))


@app.route('/delete_post/<int:post_id>')
def delete_post(post_id):
    if 'logged_in' not in session:
        return redirect(url_for('index'))
    elif not session['logged_in']:
        return redirect(url_for('index'))

    if 'is_admin' in session and session['is_admin']:
        p = Post.query.get(post_id)
    else:
        p = Post.query.get(post_id)
        u = User.query.get(p.user_id)
        if u.email != session['user_name']:
            return redirect(url_for('login'))

    db.session.delete(p)
    db.session.commit()

    if 'is_admin' in session and session['is_admin']:
        return redirect(url_for('admin_page'))
    return redirect(url_for('view_my_post'))


@app.route('/my_post')
def view_my_post():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    u = User.query.filter_by(email=session['user_name']).first()
    posts = Post.query.filter_by(user_id=u.id).all()
    return render_template('my_post.html',
                           posts=posts)


@app.route('/admin')
def admin_page():
    if 'is_admin' not in session or not session['is_admin']:
        return redirect(url_for('index'))
    users = User.query.all()
    posts = Post.query.all()
    return render_template('admin.html',
                           users=users,
                           posts=posts)


@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'is_admin' in session or session['is_admin']:
        u = User.query.get(user_id)
        posts = Post.query.filter_by(user_id=user_id).all()
        if posts is not None:
            for post in posts:
                db.session.delete(post)
        db.session.delete(u)
        db.session.commit()
        return redirect(url_for('admin_page'))
    else:
        return redirect(url_for('index'))