from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from app.models import User


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix=""
)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            username=username
        ).first()

        if not user or not user.check_password(password):
            flash("Invalid username or password.", "error")

            return render_template(
                "auth/login.html"
            )

        if not user.is_active:
            flash(
                "Your account is inactive.",
                "error"
            )

            return render_template(
                "auth/login.html"
            )

        session.clear()

        session["user_id"] = user.id
        session["role"] = user.role

        if user.role == "ADMIN":
            return redirect(
                url_for("admin.dashboard")
            )

        return redirect(
            url_for("chat.chat")
        )

    return render_template(
        "auth/login.html"
    )


@auth_bp.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("auth.login")
    )