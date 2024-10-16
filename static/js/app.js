document.addEventListener("DOMContentLoaded", function() {
    const token = localStorage.getItem("jwt");

    // Login Form
    const loginForm = document.getElementById("loginForm");
    if (loginForm) {
        loginForm.addEventListener("submit", function(e) {
            e.preventDefault();
            const username = document.getElementById("username").value;
            const password = document.getElementById("password").value;

            fetch("/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ username, password })
            })
            .then(res => res.json())
            .then(data => {
                if (data.access_token) {
                    localStorage.setItem("jwt", data.access_token);
                    document.getElementById("loginMessage").innerText = "Login successful!";
                } else {
                    document.getElementById("loginMessage").innerText = data.msg;
                }
            });
        });
    }

    // Register Form
    const registerForm = document.getElementById("registerForm");
    if (registerForm) {
        registerForm.addEventListener("submit", function(e) {
            e.preventDefault();
            const username = document.getElementById("username").value;
            const password = document.getElementById("password").value;
            const email = document.getElementById("email").value;
            const role = document.getElementById("role").value;

            fetch("/register", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ username, password, email, role })
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById("registerMessage").innerText = data.msg;
            });
        });
    }

    // Fetch and display briefs
    const briefList = document.getElementById("briefList");
    if (briefList) {
        fetch("/briefs", {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        })
        .then(res => res.json())
        .then(data => {
            data.forEach(brief => {
                const li = document.createElement("li");
                li.innerText = brief.category + " - " + brief.brand;
                briefList.appendChild(li);
            });
        });
    }

    // Create Brief Form
    const createBriefForm = document.getElementById("createBriefForm");
    if (createBriefForm) {
        createBriefForm.addEventListener("submit", function(e) {
            e.preventDefault();
            const formData = new FormData(createBriefForm);

            const briefData = {};
            formData.forEach((value, key) => briefData[key] = value);

            fetch("/briefs", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(briefData)
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById("briefMessage").innerText = data.msg;
            });
        });
    }
});
