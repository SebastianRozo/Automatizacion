import unittest

from app.flows.spreadsheets.helpers import clasificar_fecha_activacion


class ClasificarFechaActivacionTests(unittest.TestCase):
    def test_fecha_anterior_es_portabilidad(self) -> None:
        resultado = clasificar_fecha_activacion(
            "05/08/2026 09:15:00 a.m.",
            "06/08/2026",
        )
        self.assertEqual(resultado, "anterior")

    def test_misma_fecha_se_consulta_en_tns(self) -> None:
        resultado = clasificar_fecha_activacion(
            "06/08/2026 11:30:00 p.m.",
            "06/08/2026",
        )
        self.assertEqual(resultado, "misma_fecha")

    def test_fecha_posterior_se_excluye(self) -> None:
        resultado = clasificar_fecha_activacion(
            "07/08/2026 08:00:00 a.m.",
            "06/08/2026",
        )
        self.assertEqual(resultado, "posterior")

    def test_fecha_volante_invalida_falla(self) -> None:
        with self.assertRaisesRegex(ValueError, "Fecha de volante invalida"):
            clasificar_fecha_activacion(
                "06/08/2026 08:00:00 a.m.",
                "2026-08-06",
            )


if __name__ == "__main__":
    unittest.main()
