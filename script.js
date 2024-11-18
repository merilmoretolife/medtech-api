document.getElementById("taskForm").addEventListener("submit", function (event) {
    event.preventDefault(); // Prevent form submission

    // Get form data
    const productName = document.getElementById("productName").value;
    const category = document.getElementById("category").value;
    const description = document.getElementById("description").value;
    const deadline = document.getElementById("deadline").value;

    // Add task to the table
    const tableBody = document.getElementById("taskTable").querySelector("tbody");
    const newRow = document.createElement("tr");

    newRow.innerHTML = `
        <td>${productName}</td>
        <td>${category}</td>
        <td>${description}</td>
        <td>${deadline}</td>
        <td>Not Started</td>
    `;

    tableBody.appendChild(newRow);

    // Clear the form
    document.getElementById("taskForm").reset();
});
