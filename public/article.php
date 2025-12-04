<?php
include "includes/db.php";

if (!isset($_GET['id'])) {
    die("Article not found.");
}

$id = intval($_GET['id']);

$query = "
    SELECT 
        title,
        authors,
        url,
        summary,
        created_at,
        scraped_at
    FROM articles
    WHERE id = $id
    LIMIT 1
";

$result = $conn->query($query);

if ($result->num_rows === 0) {
    die("Article does not exist.");
}

$row = $result->fetch_assoc();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title><?= htmlspecialchars($row['title']) ?> - Coffee and Bytes</title>
    <link rel="stylesheet" href="assets/css/style.css">
    <link rel="icon" href="assets/images/code.png">
</head>
<body>

<header class="topbar">
    <h1>Coffee &lt;and&gt; Bytes</h1>
</header>

<div class="container article-page">

    <h2><?= htmlspecialchars($row['title']) ?></h2>

    <p class="meta">
        <strong>Author(s):</strong> <?= htmlspecialchars($row['authors']) ?><br>
        <strong>Created:</strong> <?= htmlspecialchars($row['created_at']) ?><br>
        <strong>Scraped:</strong> <?= htmlspecialchars($row['scraped_at']) ?>
    </p>

    <pre class="code-block">
<?= htmlspecialchars($row['summary']) ?>
    </pre>

    <a href="<?= htmlspecialchars($row['url']) ?>" target="_blank" class="btn external">
        View Full Article on Source Website →
    </a>

    <br><br>
    <a href="index.php" class="btn">← Back</a>

</div>
</body>
</html>
