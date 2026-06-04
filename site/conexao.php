<?php
$host = "162.241.3.46"; //
$usuario = "jeff1591_db_user"; // O usuário que você criou no cPanel
$senha = "0~nh1U!.y89|";
$banco = "jeff1591_Gaptech";

$conn = new mysqli($host, $usuario, $senha, $banco);

if ($conn->connect_error) {
    die("Falha na conexão: " . $conn->connect_error);
}
?>

