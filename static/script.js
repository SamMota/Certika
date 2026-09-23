// Função para alternar visualmente entre Abas Manual e CSV
function alternarEntrada(tipo) {
    const blocoManual = document.getElementById('bloco_manual');
    const blocoCsv = document.getElementById('bloco_csv');
    const textareaNomes = document.getElementById('textarea_nomes');
    const inputCsv = document.getElementById('csv_file');

    const lblManual = document.getElementById('lbl-manual');
    const lblCsv = document.getElementById('lbl-csv');

    if (tipo === 'manual') {
        blocoManual.style.display = 'block';
        blocoCsv.style.display = 'none';
        if (lblManual) lblManual.classList.add('active');
        if (lblCsv) lblCsv.classList.remove('active');
        if (inputCsv) inputCsv.value = '';
    } else {
        blocoManual.style.display = 'none';
        blocoCsv.style.display = 'block';
        if (lblCsv) lblCsv.classList.add('active');
        if (lblManual) lblManual.classList.remove('active');
        if (textareaNomes) {
            textareaNomes.value = '';
            atualizarContador();
            atualizarPreview();
        }
    }
}

// Evita envio acidental ao pressionar Enter no textarea
const textareaEl = document.getElementById('textarea_nomes');
if (textareaEl) {
    textareaEl.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.stopPropagation();
        }
    });
}

function toggleModelo(opcao) {
    document.getElementById('box-lista').style.display = opcao === 'lista' ? 'block' : 'none';
    document.getElementById('box-upload').style.display = opcao === 'upload' ? 'block' : 'none';

    if (opcao === 'lista') {
        document.getElementById('lbl-lista').classList.add('active');
        document.getElementById('lbl-upload').classList.remove('active');
    } else {
        document.getElementById('lbl-upload').classList.add('active');
        document.getElementById('lbl-lista').classList.remove('active');
    }
    carregarImagemModelo();
}

function toTitleCase(str) {
    return str.toLowerCase().replace(/(?:^|\s|-)\S/g, function (a) {
        return a.toUpperCase();
    });
}

function aplicarFormatacaoNomes() {
    const textarea = document.getElementById('textarea_nomes');
    const formato = document.getElementById('formato_nome').value;

    if (!textarea || !textarea.value.trim()) return;

    const linhas = textarea.value.split('\n');
    const linhasFormatadas = linhas.map(linha => {
        if (formato === 'upper') return linha.toUpperCase();
        if (formato === 'title') return toTitleCase(linha);
        return linha;
    });

    textarea.value = linhasFormatadas.join('\n');
    atualizarContador();
    atualizarPreview();
}

// Validação e Limpeza Inteligente de Nomes
function limparEValidarLista() {
    const textarea = document.getElementById('textarea_nomes');
    const msgSpan = document.getElementById('validationMsg');

    if (!textarea || !textarea.value.trim()) {
        msgSpan.className = 'validation-msg error';
        msgSpan.innerText = 'Nenhum nome inserido.';
        return;
    }

    const linhasOriginais = textarea.value.split('\n');
    let duplicadosEncontrados = 0;
    let linhasVaziasRemovidas = 0;

    const nomesUnicos = [];
    const nomesVistos = new Set();

    linhasOriginais.forEach(linha => {
        let nomeLimpo = linha.trim().replace(/[\t\r]/g, '').replace(/\s+/g, ' ');

        if (nomeLimpo === '') {
            linhasVaziasRemovidas++;
            return;
        }

        const chaveUnica = nomeLimpo.toLowerCase();
        if (nomesVistos.has(chaveUnica)) {
            duplicadosEncontrados++;
        } else {
            nomesVistos.add(chaveUnica);
            nomesUnicos.push(nomeLimpo);
        }
    });

    textarea.value = nomesUnicos.join('\n');
    atualizarContador();
    atualizarPreview();

    if (duplicadosEncontrados > 0 || linhasVaziasRemovidas > 0) {
        msgSpan.className = 'validation-msg warning';
        let aviso = [];
        if (duplicadosEncontrados > 0) aviso.push(`${duplicadosEncontrados} duplicado(s) removido(s)`);
        if (linhasVaziasRemovidas > 0) aviso.push(`${linhasVaziasRemovidas} linha(s) vazia(s) limpa(s)`);
        msgSpan.innerText = `✓ ${aviso.join(', ')}.`;
    } else {
        msgSpan.className = 'validation-msg success';
        msgSpan.innerText = '✓ Lista válida e sem duplicados!';
    }

    setTimeout(() => {
        msgSpan.innerText = '';
    }, 5000);
}

const badge = document.getElementById('counterBadge');
const msgSpan = document.getElementById('validationMsg');

function atualizarContador() {
    if (!textareaEl || !badge) return;
    const lines = textareaEl.value.split('\n').filter(line => line.trim() !== '');
    const count = lines.length;
    badge.innerText = `${count} certificado${count === 1 ? '' : 's'}`;

    const nomesMinusculos = lines.map(l => l.trim().toLowerCase());
    const temDuplicado = new Set(nomesMinusculos).size !== nomesMinusculos.length;

    if (temDuplicado && msgSpan && !msgSpan.innerText.includes('removido')) {
        msgSpan.className = 'validation-msg warning';
        msgSpan.innerText = '⚠️ Nomes duplicados detectados';
    } else if (!temDuplicado && msgSpan && msgSpan.innerText.includes('duplicados detectados')) {
        msgSpan.innerText = '';
    }
}

if (textareaEl) {
    textareaEl.addEventListener('input', () => {
        atualizarContador();
        atualizarPreview();
    });
}

// Dynamic Live Preview no Canvas
const canvas = document.getElementById('certPreview');
const ctx = canvas ? canvas.getContext('2d') : null;
const imgModelo = new Image();
imgModelo.crossOrigin = "anonymous";

function carregarImagemModelo() {
    const radioUpload = document.querySelector('input[name="origem_modelo"][value="upload"]');

    if (radioUpload && radioUpload.checked) {
        const fileInput = document.querySelector('input[name="file_upload"]');
        if (fileInput && fileInput.files && fileInput.files[0]) {
            const reader = new FileReader();
            reader.onload = function (e) {
                imgModelo.src = e.target.result;
            };
            reader.readAsDataURL(fileInput.files[0]);
            return;
        }
    }

    const selectModelo = document.querySelector('select[name="modelo_lista"]');
    const nomeModelo = selectModelo ? selectModelo.value : '';

    if (nomeModelo) {
        imgModelo.src = `/image/${nomeModelo}?t=${new Date().getTime()}`;
    }
}

function atualizarPreview() {
    if (!canvas || !ctx || !imgModelo.complete || imgModelo.naturalWidth === 0) return;

    canvas.width = imgModelo.naturalWidth;
    canvas.height = imgModelo.naturalHeight;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(imgModelo, 0, 0);

    const fontSizeInput = document.querySelector('input[name="font_size"]');
    const posYInput = document.querySelector('input[name="pos_y_factor"]');
    const colorInput = document.querySelector('input[name="cor_hex"]');

    const fontSize = fontSizeInput ? fontSizeInput.value : 60;
    const posYFactor = posYInput ? posYInput.value : 2.5;
    const hexColor = colorInput ? colorInput.value : '#000000';

    let textoExemplo = 'Nome do Participante Exemplo';
    if (textareaEl && textareaEl.value.trim()) {
        textoExemplo = textareaEl.value.split('\n').find(l => l.trim() !== '') || textoExemplo;
    }

    ctx.font = `bold ${fontSize}px "Plus Jakarta Sans", sans-serif`;
    ctx.fillStyle = hexColor;
    ctx.textAlign = 'center';

    const posY = canvas.height / posYFactor;
    ctx.fillText(textoExemplo, canvas.width / 2, posY);
}

imgModelo.onload = atualizarPreview;

document.querySelectorAll('input, select, textarea').forEach(element => {
    element.addEventListener('change', () => {
        carregarImagemModelo();
        atualizarPreview();
    });
    element.addEventListener('input', atualizarPreview);
});

window.addEventListener('DOMContentLoaded', carregarImagemModelo);

// Intercepta o envio do formulário
const form = document.getElementById('certForm');
const btnSubmit = document.getElementById('btnSubmit');
const btnText = document.getElementById('btnText');
const btnIcon = document.getElementById('btnIcon');
const btnSpinner = document.getElementById('btnSpinner');

if (form) {
    form.addEventListener('submit', function (e) {
        e.preventDefault();

        const checkboxEmail = document.getElementById('enviar_emails');
        
        if (checkboxEmail && checkboxEmail.checked) {
            const confirmModal = document.getElementById('confirmEmailModal');
            if (confirmModal) {
                confirmModal.classList.remove('hidden');
                return;
            }
        }

        executarEnvioDados();
    });
}

// Botão Cancelar na tela flutuante de confirmação
const btnCancelarEnvio = document.getElementById('btnCancelarEnvio');
if (btnCancelarEnvio) {
    btnCancelarEnvio.addEventListener('click', function () {
        const confirmModal = document.getElementById('confirmEmailModal');
        if (confirmModal) confirmModal.classList.add('hidden');
    });
}

// Botão Confirmar na tela flutuante de confirmação
const btnConfirmarEnvio = document.getElementById('btnConfirmarEnvio');
if (btnConfirmarEnvio) {
    btnConfirmarEnvio.addEventListener('click', function () {
        const confirmModal = document.getElementById('confirmEmailModal');
        if (confirmModal) confirmModal.classList.add('hidden');
        executarEnvioDados();
    });
}

async function executarEnvioDados() {
    const formData = new FormData(form);
    const checkboxEmail = document.getElementById('enviar_emails');
    const envioAtivo = checkboxEmail && checkboxEmail.checked;

    if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.classList.add('btn-loading-state');
    }
    if (btnText) btnText.innerText = envioAtivo ? 'Enviando e-mails...' : 'Gerando certificados...';
    if (btnIcon) btnIcon.style.display = 'none';
    if (btnSpinner) btnSpinner.classList.remove('hidden');

    const toast = document.getElementById('emailProgressToast');
    const progressText = document.getElementById('progressText');

    if (envioAtivo && toast) {
        toast.classList.remove('hidden');
        if (progressText) progressText.innerText = 'A iniciar conexão SMTP...';
    }

    try {
        const response = await window.fetch('/', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            if (toast) toast.classList.add('hidden');
            alert('Ocorreu um erro ao processar os certificados.');
            return;
        }

        if (envioAtivo) {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.replace('data: ', ''));
                            
                            if (data.status === 'progresso' && progressText) {
                                progressText.innerText = data.mensagem;
                            } else if (data.status === 'erro') {
                                if (toast) toast.classList.add('hidden');
                                alert('Erro no envio SMTP: ' + data.mensagem);
                                return;
                            } else if (data.status === 'concluido') {
                                if (toast) toast.classList.add('hidden');
                                window.location.href = '/baixar-zip';
                                
                                const csvInput = document.getElementById('csv_file');
                                if (csvInput) csvInput.value = '';
                                if (checkboxEmail) checkboxEmail.checked = false;
                                const camposSmtp = document.getElementById('campos_smtp');
                                if (camposSmtp) camposSmtp.style.display = 'none';

                                let successModal = document.getElementById('successModal');
                                if (successModal) successModal.classList.remove('hidden');

                                // Quebra o ciclo while e fecha o stream para parar de carregar a aba
                                break;
                            }
                        } catch (err) {
                            console.error('Erro ao interpretar JSON:', err);
                        }
                    }
                }
            }
        } else {
            if (toast) toast.classList.add('hidden');
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'certificados.zip';
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

            const csvInput = document.getElementById('csv_file');
            if (csvInput) csvInput.value = '';

            let successModal = document.getElementById('successModal');
            if (successModal) successModal.classList.remove('hidden');
        }
    } catch (error) {
        if (toast) toast.classList.add('hidden');
        console.error('Erro:', error);
        alert('Erro de conexão com o servidor.');
    } finally {
        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.classList.remove('btn-loading-state');
        }
        if (btnText) btnText.innerText = 'Gerar Pacote ZIP';
        if (btnIcon) btnIcon.style.display = 'inline';
        if (btnSpinner) btnSpinner.classList.add('hidden');
    }
}

function toggleEmailConfig(checkbox) {
    const camposSmtp = document.getElementById('campos_smtp');
    if (camposSmtp) {
        camposSmtp.style.display = checkbox.checked ? 'flex' : 'none';
    }
}

// Função do Botão de E-mail de Teste
async function dispararEmailTeste() {
    const statusSpan = document.getElementById('testeStatus');
    const btnTeste = document.getElementById('btnTestarEmail');
    
    const emailInput = document.querySelector('input[name="smtp_email"]');
    const senhaInput = document.querySelector('input[name="smtp_senha"]');

    if (!emailInput || !emailInput.value.trim() || !senhaInput || !senhaInput.value.trim()) {
        if (statusSpan) {
            statusSpan.style.color = '#dc2626';
            statusSpan.innerText = '⚠️ Preencha o e-mail e a senha primeiro!';
        }
        return;
    }

    if (btnTeste) btnTeste.disabled = true;
    if (statusSpan) {
        statusSpan.style.color = '#2563eb';
        statusSpan.innerText = '⏳ A enviar teste...';
    }

    const formData = new FormData(form);

    try {
        const response = await window.fetch('/testar-email', {
            method: 'POST',
            body: formData
        });

        const resultado = await response.json();

        if (response.ok && resultado.sucesso) {
            if (statusSpan) {
                statusSpan.style.color = '#16a34a';
                statusSpan.innerText = '✓ Teste enviado com sucesso!';
            }
        } else {
            if (statusSpan) {
                statusSpan.style.color = '#dc2626';
                statusSpan.innerText = '❌ ' + (resultado.mensagem || 'Erro ao enviar.');
            }
        }
    } catch (error) {
        console.error('Erro:', error);
        if (statusSpan) {
            statusSpan.style.color = '#dc2626';
            statusSpan.innerText = '❌ Erro de conexão.';
        }
    } finally {
        if (btnTeste) btnTeste.disabled = false;
    }
}

// Ação do botão de recomeçar (dentro do modal de sucesso)
document.addEventListener('click', function (e) {
    if (e.target && e.target.id === 'btnRecomecar') {
        if (form) form.reset();
        window.location.href = window.location.pathname;
    }
});

// Função para corrigir erros comuns de digitação em e-mails antes de enviar
function corrigirErrosDeEmail(email) {
    if (!email) return email;
    let limpo = email.trim().toLowerCase();
    
    const correcoesGmail = ['@gmal.com', '@gmil.com', '@gamil.com', '@gmai.com', '@gmal.con', '@gmail.con', '@gmailcom'];
    correcoesGmail.forEach(errado => {
        if (limpo.endsWith(errado)) {
            limpo = limpo.replace(errado, '@gmail.com');
        }
    });

    if (limpo.endsWith('@hotmaill.com') || limpo.endsWith('@hotmai.com')) {
        limpo = limpo.replace(/@hotmaill?\.com/, '@hotmail.com');
    }
    
    return limpo;
}