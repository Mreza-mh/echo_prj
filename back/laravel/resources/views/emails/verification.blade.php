<!DOCTYPE html>
<html lang="{{ $locale }}">
<head>
    <meta charset="UTF-8">
    <title>Email Verification</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f5f5f5;
            padding: 0;
            margin: 0;
        }

        .container {
            max-width: 480px;
            background: #ffffff;
            margin: 40px auto;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            text-align: center;
        }

        h2 {
            color: #333;
            margin-bottom: 10px;
        }

        .code-box {
            background: #005cbb;
            color: white;
            padding: 14px 20px;
            font-size: 28px;
            letter-spacing: 6px;
            border-radius: 6px;
            margin: 20px 0;
            display: inline-block;
        }

        p {
            color: #555;
            line-height: 1.7;
            font-size: 15px;
        }

        .footer {
            margin-top: 20px;
            color: #888;
            font-size: 13px;
        }
    </style>
</head>

<body>
<div class="container">

    <h2>Email Verification</h2>

    <p>Use the code below to verify your email address:</p>

    <div class="code-box">{{ $code }}</div>

    <p class="footer">
        If you did not request this, please ignore this email.
    </p>

</div>
</body>
</html>
