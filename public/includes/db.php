<?php
$host = "localhost";
$user = "admin";
$pass = "admin";
$dbname = "technews";

$conn = new mysqli($host, $user, $pass, $dbname);

if ($conn->connect_error) {
    die("Database connection failed: " . $conn->connect_error);
}
?>
