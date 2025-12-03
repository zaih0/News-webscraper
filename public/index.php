<?php
include "includes/db.php";

// Fetch latest articles
$query = "
    SELECT id, title, authors, summary, created_at
    FROM articles
    ORDER BY created_at DESC
    LIMIT 50
";

$result = $conn->query($query);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Coffee and Bytes - Tech News</title>
    <link rel="stylesheet" href="assets/css/style.css">
    <script src="assets/script.js" defer></script>
</head>

<body>

<header class="topbar">
    <h1>Coffee &lt;and&gt; Bytes</h1>
</header>

<div class="container">

    <h2 class="section-title">Latest Tech Articles</h2>

    <div class="articles-grid">

        <?php while ($row = $result->fetch_assoc()): ?>
            <div class="article-card">

                <h3 class="article-title">
                    <?= htmlspecialchars($row['title']) ?>
                </h3>

                <p class="article-meta">
                    <strong>Authors:</strong> <?= htmlspecialchars($row['authors']) ?><br>
                    <strong>Created:</strong> <?= htmlspecialchars($row['created_at']) ?>
                </p>

                <pre class="code-block preview">
<?= htmlspecialchars($row['summary']) ?>
                </pre>

                <a href="article.php?id=<?= $row['id'] ?>" class="btn">
                    Read More →
                </a>

            </div>
        <?php endwhile; ?>

    </div>

</div>

</body>
</html>
