-- para a execucao com mensagem clara se o salt nao foi informado
SELECT CASE
    WHEN getvariable('salt') IS NULL OR length(getvariable('salt')) = 0
    THEN error('ALUNO_HASH_SALT ausente: copie .env.example para .env e defina o salt antes de rodar a silver')
END AS salt_ok;
