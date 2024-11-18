// Mapping categories to responsible individuals
const categoryMapping = {
    "Artwork Approval": ["Neha Patel", "Kruti Bilakhia"],
    "CE Technical File Chapters for EndoSurgery": ["Asma Shaikh", "Chetan Patel", "Rahul Fidai", "Bhavin Choradiya", "Surbhi Patel"],
    "510(k) EndoSurgery": ["Asma Shaikh", "Chetan Patel"],
    "CE Technical File Chapters for Healthcare": ["Bittu Jha", "Prem Patil"],
    "510(k) Healthcare": ["Bittu Jha"],
    "QMS Setup": ["Neha Patel", "Kruti Bilakhia", "Rahul Fidai"],
    "Risk Management and Usability": ["Bittu Jha", "Prem Patil", "Neel Naik", "Surbhi Patel"],
    "Biocompatibility Testing and Biological Report": ["Asma Shaikh", "Niyati Patel"],
    "Clinical Documentation": ["Shriya and Team", "Senthil and Team"],
    "PMS/PSUR": ["Aniket Arekar", "Pinki Purohit", "Senthil and Team"],
    "DCGI Related Work": ["Punita Patel and Team"],
    "Design File Preparation": ["Bittu Jha", "Surbhi Patel", "Chetan Patel", "Asma Shaikh", "Rahul Fidai", "Neel Naik", "Roshani Upadhyay", "Bhavin Choradiya"]
};

// Function to get the first available person from the category
function assignPerson(category) {
    if (categoryMapping[category]) {
        // Rotate through the available people for the category
        const assignedPerson = categoryMapping[category].shift();
        categoryMapping[category].push(assignedPerson); // Rotate to the back of the list
        return assignedPerson;
    }
    return "Unassigned";
}

// Handle form submission
document.getElementById("taskForm").addEventListener("submit", function (event) {
    event.preventDefault(); // Prevent form submission

    // Get form data
    const productName = document.getElementById("productName").value;
    const category = document.getElementById("category").value;
    const description = document.getElementById("description").value;
    const deadline = document.getElementById("deadline").value;

    // Auto-assign person based on category
    const assignedPerson = assignPerson(category);

    // Add task to the table
    const tableBody = document.getElementById("taskTable").querySelector("tbody");
    const newRow = document.createElement("tr");

    newRow.innerHTML = `
        <td>${productName}</td>
        <td>${category}</td>
        <td>${description}</td>
        <td>${deadline}</td>
        <td>${assignedPerson}</td>
    `;

    tableBody.appendChild(newRow);

    // Clear the form
    document.getElementById("taskForm").reset();
});
