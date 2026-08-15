from __future__ import annotations

import time


def imprimir_copias(driver, copias: int, espera_entre_copias: float = 3) -> None:
    """Envia al navegador la cantidad indicada de trabajos de impresion."""
    for numero_copia in range(1, copias + 1):
        print(f"Enviando copia {numero_copia} de {copias} a la impresora.", flush=True)
        driver.execute_script("window.print();")
        time.sleep(espera_entre_copias)


def aplicar_configuracion_impresion(driver, ajustar_zoom: bool = False) -> None:
    """Aplica a la planilla los mismos estilos usados en la impresion real."""
    driver.execute_script(
        """
        const previous = document.getElementById('automatizacion-print-style');
        if (previous) previous.remove();

        const style = document.createElement('style');
        style.id = 'automatizacion-print-style';
        style.textContent = `
            @page {
                size: letter portrait;
                margin: 2mm;
            }

            @media print {
                html, body {
                    width: 100% !important;
                    min-width: 0 !important;
                    max-width: none !important;
                    height: auto !important;
                    min-height: 0 !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    overflow: visible !important;
                }

                *, *::before, *::after {
                    box-sizing: border-box !important;
                }

                body {
                    /* El cuerpo es mas ancho antes de aplicar el 80% para que
                       la tabla aproveche casi todo el ancho imprimible. */
                    width: 275mm !important;
                    max-width: 275mm !important;
                    background: #fff !important;
                    color: #000 !important;
                    font-size: 9pt !important;
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }

                .container,
                .container-fluid,
                .content,
                .main-content,
                .BodyMaster,
                form {
                    width: 100% !important;
                    min-width: 0 !important;
                    max-width: none !important;
                    margin-left: 0 !important;
                    margin-right: 0 !important;
                    overflow: visible !important;
                }

                .TableMaster,
                .cabecera-planilla,
                .tableCompletePl {
                    width: 100% !important;
                    min-width: 0 !important;
                    max-width: 100% !important;
                }

                table {
                    border-collapse: collapse !important;
                    table-layout: auto !important;
                    max-width: 100% !important;
                    break-inside: auto;
                    page-break-inside: auto;
                }

                .tableCompletePl {
                    table-layout: fixed !important;
                    font-size: 8pt !important;
                }

                /* Reparto estable para que las columnas numericas no queden
                   comprimidas por nombres, ICCID, fechas o descripciones. */
                .tableCompletePl th:nth-child(1)  { width: 2.5% !important; }
                .tableCompletePl th:nth-child(2)  { width: 6% !important; }
                .tableCompletePl th:nth-child(3)  { width: 9% !important; }
                .tableCompletePl th:nth-child(4)  { width: 10% !important; }
                .tableCompletePl th:nth-child(5)  { width: 5% !important; }
                .tableCompletePl th:nth-child(6)  { width: 5% !important; }
                .tableCompletePl th:nth-child(7)  { width: 4% !important; }
                .tableCompletePl th:nth-child(8)  { width: 7% !important; }
                .tableCompletePl th:nth-child(9)  { width: 8% !important; }

                .tableCompletePl th:nth-child(n+10) {
                    width: 3.35% !important;
                }

                thead {
                    display: table-header-group;
                }

                tfoot {
                    display: table-footer-group;
                }

                tr, img {
                    break-inside: avoid !important;
                    page-break-inside: avoid !important;
                }

                td, th {
                    height: auto !important;
                    padding: 1px !important;
                    line-height: 1.1 !important;
                    color: #000 !important;
                    border-color: #000 !important;
                    overflow: visible !important;
                    overflow-wrap: normal !important;
                    word-break: normal !important;
                    vertical-align: middle !important;
                }

                td, th {
                    white-space: normal !important;
                }

                .tableCompletePl td,
                .tableCompletePl th {
                    padding: 0 2px !important;
                    font-size: 8pt !important;
                    line-height: 0.78 !important;
                    overflow-wrap: anywhere !important;
                }

                img, svg, canvas {
                    max-width: 100% !important;
                    height: auto !important;
                }

                button,
                input[type='button'],
                input[type='submit'],
                .no-print {
                    display: none !important;
                }

                html.automatizacion-print-compact body {
                    font-size: 8.5pt !important;
                }

                html.automatizacion-print-compact table,
                html.automatizacion-print-compact td,
                html.automatizacion-print-compact th {
                    font-size: 7pt !important;
                    line-height: 0.78 !important;
                }
            }
        `;
        document.head.appendChild(style);
        document.documentElement.classList.toggle(
            'automatizacion-print-compact',
            Boolean(arguments[0])
        );
        window.scrollTo(0, 0);
        """,
        ajustar_zoom,
    )
