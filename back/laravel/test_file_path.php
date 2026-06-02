<?php

// تست normalizeFileAddress
$basePath = realpath(__DIR__ . '/public/echos');

echo "Base Path: $basePath\n\n";

// تست 1: مسیر نسبی از MongoDB
$testPath1 = "2/2026-06-02/a4c/media/measurements/End_Sistol_la.jpg";
echo "Test 1 - MongoDB Path:\n";
echo "  Input: $testPath1\n";

$fullPath1 = $basePath . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $testPath1);
echo "  Full Path: $fullPath1\n";

$realPath1 = realpath($fullPath1);
echo "  Real Path: " . ($realPath1 ?: 'FALSE') . "\n";

if ($realPath1 && file_exists($realPath1)) {
    echo "  ✅ File EXISTS!\n";
    echo "  File Size: " . filesize($realPath1) . " bytes\n";
} else {
    echo "  ❌ File NOT FOUND!\n";
}

echo "\n" . str_repeat("=", 80) . "\n\n";

// تست 2: مسیر URL encoded
$testPath2 = "2/2026-06-02/a4c/media/measurements/End_Sistol_la.jpg";
echo "Test 2 - URL Encoded:\n";
echo "  Input: $testPath2\n";

$decoded = rawurldecode($testPath2);
echo "  Decoded: $decoded\n";

$fullPath2 = $basePath . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $decoded);
$realPath2 = realpath($fullPath2);
echo "  Real Path: " . ($realPath2 ?: 'FALSE') . "\n";

if ($realPath2 && file_exists($realPath2)) {
    echo "  ✅ File EXISTS!\n";
} else {
    echo "  ❌ File NOT FOUND!\n";
}

echo "\n" . str_repeat("=", 80) . "\n\n";

// لیست همه فایل‌های موجود
echo "Available files in 2/2026-06-02/a4c/media/measurements:\n";
$measurementsDir = $basePath . '/2/2026-06-02/a4c/media/measurements';
if (is_dir($measurementsDir)) {
    $files = scandir($measurementsDir);
    foreach ($files as $file) {
        if ($file !== '.' && $file !== '..') {
            echo "  - $file\n";
        }
    }
} else {
    echo "  Directory not found: $measurementsDir\n";
}
