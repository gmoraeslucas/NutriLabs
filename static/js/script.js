
        function validateForm() {
            var password = document.getElementById("password").value;
            var confirm_password = document.getElementById("confirm_password").value;
            var error_message = document.getElementById("password_error");

            if (password != confirm_password) {
                error_message.textContent = "As senhas não coincidem";
                return false;
            } else {
                error_message.textContent = "";
                return true;
            }
        }

        function toggleSummary(subscriptionId) {
            console.log("Toggle summary for subscription ID:", subscriptionId); // Debug log
            var summary = document.getElementById('summary-' + subscriptionId);
            if (summary.style.display === 'none' || summary.style.display === '') {
                summary.style.display = 'block';
            } else {
                summary.style.display = 'none';
            }
        }


    