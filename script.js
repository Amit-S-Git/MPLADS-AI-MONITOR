function showDetails(project, score) {

    document.getElementById("projectID").innerText =
        project;

    document.getElementById("riskScore").innerText =
        "Risk Score: " + score + "/100";

    document.getElementById("popup").style.display =
        "grid";
}


function closePopup() {

    document.getElementById("popup").style.display =
        "none";
}


function runAI() {

    alert(
        "AI Risk Analysis Complete!\n\n" +
        "7 risk indicators detected.\n" +
        "3 High Risk projects found."
    );
}


function generateReport() {

    alert(
        "Demo Report Generated!\n\n" +
        "MPLADS Monitoring Report\n" +
        "High Risk Projects: 35\n" +
        "Delayed Projects: 120"
    );
}


function showMessage() {

    alert(
        "Map module will show all MPLADS projects geographically."
    );
}


function toggleSidebar() {
    document
        .querySelector(".app")
        .classList.toggle("sidebar-hidden");
}
