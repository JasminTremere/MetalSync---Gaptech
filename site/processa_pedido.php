<?php
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json");

include 'conexao.php';

$json = file_get_contents('php://input');
$data = json_decode($json, true);

if ($data) {
    $id = $data['pedido_id'];
    $cliente = $data['cliente'];
    $data_ped = $data['data'];
    $total = $data['total'];

    // Inserindo na tabela principal
    $sql = "INSERT INTO db_pedido_pedidos (pedido_id, cliente, data_emissao, valor_total) 
            VALUES ('$id', '$cliente', '$data_ped', '$total')";

    if ($conn->query($sql) === TRUE) {
        echo json_encode(["status" => "sucesso"]);
    } else {
        echo json_encode(["status" => "erro", "msg" => $conn->error]);
    }
}
$conn->close();
?>