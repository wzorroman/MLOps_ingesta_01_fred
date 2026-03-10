#!/usr/bin/env python3
"""
Test FRED Historical Data Sample
================================
Descarga muestras aleatorias de días históricos (2019-2025)
para validar la consistencia de los datos FRED.

Uso:
    python scripts/test_fred_historical_sample.py --api-key TU_API_KEY --samples 20


    # Instalar dependencias
pip install requests pandas numpy

# Ejecutar con 20 muestras aleatorias
python test_fred_historical_sample.py --api-key TU_API_KEY --samples 20

# O con más muestras
python test_fred_historical_sample.py --api-key TU_API_KEY --samples 30
"""

import argparse
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from pathlib import Path
import random
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# FRED API endpoints
FRED_BASE = "https://api.stlouisfed.org/fred"

# Series a probar
FRED_SERIES = {
    'DXY': {
        'id': 'DTWEXBGS',
        'name': 'Dólar Index (Broad)',
        'description': 'Nominal Broad U.S. Dollar Index'
    },
    'VIX': {
        'id': 'VIXCLS',
        'name': 'VIX Volatility Index',
        'description': 'CBOE Volatility Index: VIX'
    },
    'US10Y': {
        'id': 'DGS10',
        'name': '10-Year Treasury Yield',
        'description': 'Market Yield on U.S. Treasury Securities at 10-Year'
    }
}

def generate_random_dates(years_range=(2019, 2025), num_samples=20):
    """
    Genera fechas aleatorias dentro del rango especificado
    """
    start_date = datetime(years_range[0], 1, 1)
    end_date = datetime(years_range[1], 12, 31)

    # Generar fechas aleatorias
    all_dates = []
    for _ in range(num_samples * 3):  # Generar más para filtrar fines de semana
        random_days = random.randint(0, (end_date - start_date).days)
        random_date = start_date + timedelta(days=random_days)
        all_dates.append(random_date)

    # Filtrar para tener solo días de semana (lunes-viernes)
    weekdays = [d for d in all_dates if d.weekday() < 5]

    # Tomar muestra única y ordenada
    selected = sorted(set(weekdays))[:num_samples]

    logger.info(f"📅 Fechas seleccionadas ({len(selected)} muestras):")
    for date in selected:
        logger.info(f"   • {date.strftime('%Y-%m-%d')} ({date.strftime('%A')})")

    return selected

def get_series_observations(api_key: str, series_id: str, date: datetime) -> dict:
    """
    Obtiene observación para una fecha específica
    """
    url = f"{FRED_BASE}/series/observations"

    # Buscar ±3 días alrededor de la fecha objetivo
    start = (date - timedelta(days=3)).strftime('%Y-%m-%d')
    end = (date + timedelta(days=3)).strftime('%Y-%m-%d')

    params = {
        'series_id': series_id,
        'api_key': api_key,
        'file_type': 'json',
        'observation_start': start,
        'observation_end': end,
        'sort_order': 'asc'
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if 'observations' not in data or not data['observations']:
            return {
                'date': date.strftime('%Y-%m-%d'),
                'value': None,
                'status': 'no_data'
            }

        # Buscar la fecha exacta o la más cercana
        for obs in data['observations']:
            obs_date = datetime.strptime(obs['date'], '%Y-%m-%d')
            if obs_date.date() == date.date():
                return {
                    'date': obs['date'],
                    'value': float(obs['value']) if obs['value'] != '.' else None,
                    'status': 'exact_match'
                }

        # Si no hay match exacto, tomar el más cercano
        closest = min(data['observations'],
                     key=lambda x: abs(datetime.strptime(x['date'], '%Y-%m-%d') - date))

        closest_date = datetime.strptime(closest['date'], '%Y-%m-%d')
        days_diff = abs((closest_date - date).days)

        return {
            'date': closest['date'],
            'value': float(closest['value']) if closest['value'] != '.' else None,
            'status': 'closest_match',
            'target_date': date.strftime('%Y-%m-%d'),
            'days_diff': days_diff
        }

    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            'date': date.strftime('%Y-%m-%d'),
            'value': None,
            'status': 'error',
            'error': str(e)
        }

def test_historical_samples(api_key: str, num_samples: int = 20):
    """
    Prueba muestras históricas para todas las series
    """
    logger.info("=" * 80)
    logger.info("📊 TEST FRED - MUESTRAS HISTÓRICAS ALEATORIAS (2019-2025)")
    logger.info("=" * 80)

    # Generar fechas aleatorias
    test_dates = generate_random_dates(num_samples=num_samples)

    # Resultados por serie
    results = {series: [] for series in FRED_SERIES.keys()}

    for i, test_date in enumerate(test_dates, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"📌 MUESTRA #{i}: {test_date.strftime('%Y-%m-%d')}")
        logger.info(f"{'='*60}")

        for series_key, series_info in FRED_SERIES.items():
            logger.info(f"\n🔍 {series_info['name']} ({series_info['id']}):")

            result = get_series_observations(api_key, series_info['id'], test_date)

            if result['status'] == 'exact_match':
                logger.info(f"   ✅ Match exacto: {result['date']} = {result['value']}")
            elif result['status'] == 'closest_match':
                logger.info(f"   ⚠️ Match cercano: {result['date']} (target: {result['target_date']}, diff: {result['days_diff']} días) = {result['value']}")
            elif result['status'] == 'no_data':
                logger.info(f"   ❌ Sin datos")
            else:
                logger.info(f"   ❌ Error: {result.get('error', 'Unknown')}")

            results[series_key].append(result)

            # Pequeña pausa para no saturar API
            time.sleep(0.3)

    return results, test_dates

def analyze_results(results: dict, test_dates: list):
    """
    Analiza los resultados de las muestras
    """
    logger.info("\n" + "=" * 80)
    logger.info("📈 ANÁLISIS DE RESULTADOS")
    logger.info("=" * 80)

    # Resumen por serie
    for series_key, series_results in results.items():
        series_info = FRED_SERIES[series_key]

        logger.info(f"\n{series_info['name']} ({series_info['id']}):")
        logger.info("-" * 50)

        # Estadísticas
        total = len(series_results)
        exact = sum(1 for r in series_results if r['status'] == 'exact_match')
        closest = sum(1 for r in series_results if r['status'] == 'closest_match')
        no_data = sum(1 for r in series_results if r['status'] == 'no_data')
        errors = sum(1 for r in series_results if r['status'] == 'error')

        logger.info(f"   📊 Total muestras: {total}")
        logger.info(f"   ✅ Match exacto: {exact} ({exact/total*100:.1f}%)")
        logger.info(f"   ⚠️ Match cercano: {closest} ({closest/total*100:.1f}%)")
        logger.info(f"   ❌ Sin datos: {no_data} ({no_data/total*100:.1f}%)")
        logger.info(f"   🔴 Errores: {errors} ({errors/total*100:.1f}%)")

        # Días de diferencia promedio en matches cercanos
        closest_diffs = [r.get('days_diff', 0) for r in series_results if r['status'] == 'closest_match' and 'days_diff' in r]
        if closest_diffs:
            avg_diff = sum(closest_diffs) / len(closest_diffs)
            logger.info(f"   📏 Diferencia promedio (matches cercanos): {avg_diff:.1f} días")

        # Valores obtenidos
        values = [r['value'] for r in series_results if r['value'] is not None]
        if values:
            logger.info(f"   📈 Valores: min={min(values):.2f}, max={max(values):.2f}, media={np.mean(values):.2f}")

    # Análisis por año
    logger.info("\n📅 ANÁLISIS POR AÑO:")
    logger.info("-" * 50)

    for year in range(2019, 2026):
        year_indices = [i for i, d in enumerate(test_dates) if d.year == year]
        if year_indices:
            logger.info(f"\n{year}: {len(year_indices)} muestras")

            for series_key in FRED_SERIES.keys():
                year_results = [results[series_key][i] for i in year_indices]
                available = sum(1 for r in year_results if r['value'] is not None)
                logger.info(f"   {series_key}: {available}/{len(year_indices)} disponibles ({available/len(year_indices)*100:.1f}%)")

def save_sample_report(results: dict, test_dates: list, output_dir: str = "data/fred_samples"):
    """
    Guarda reporte detallado de las muestras
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Crear DataFrame combinado
    rows = []
    for i, test_date in enumerate(test_dates):
        row = {
            'target_date': test_date.strftime('%Y-%m-%d'),
            'target_year': test_date.year,
            'target_month': test_date.month,
            'target_day': test_date.day,
            'target_weekday': test_date.strftime('%A')
        }
        for series_key in FRED_SERIES.keys():
            result = results[series_key][i]
            row[f'{series_key}_date'] = result.get('date', '')
            row[f'{series_key}_value'] = result.get('value', '')
            row[f'{series_key}_status'] = result.get('status', '')
            if 'days_diff' in result:
                row[f'{series_key}_days_diff'] = result.get('days_diff', '')
        rows.append(row)

    df = pd.DataFrame(rows)

    # Guardar CSV
    csv_file = output_path / f"fred_samples_{timestamp}.csv"
    df.to_csv(csv_file, index=False)
    logger.info(f"\n💾 Reporte CSV guardado: {csv_file}")

    # Guardar resumen markdown
    md_file = output_path / f"fred_samples_report.md"
    with open(md_file, 'w') as f:
        f.write("# FRED Historical Data Sample Report\n\n")
        f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Muestras: {len(test_dates)} días aleatorios (2019-2025)\n\n")

        f.write("## Resumen por Serie\n\n")
        for series_key, series_results in results.items():
            series_info = FRED_SERIES[series_key]
            f.write(f"### {series_info['name']} (`{series_info['id']}`)\n\n")

            exact = sum(1 for r in series_results if r['status'] == 'exact_match')
            closest = sum(1 for r in series_results if r['status'] == 'closest_match')
            no_data = sum(1 for r in series_results if r['status'] == 'no_data')
            total = len(series_results)

            f.write(f"- **Total muestras**: {total}\n")
            f.write(f"- **Match exacto**: {exact} ({exact/total*100:.1f}%)\n")
            f.write(f"- **Match cercano**: {closest} ({closest/total*100:.1f}%)\n")
            f.write(f"- **Sin datos**: {no_data} ({no_data/total*100:.1f}%)\n\n")

            # Mostrar muestra de valores
            f.write("| # | Target | Real | Valor | Status |\n")
            f.write("|---|--------|------|-------|--------|\n")
            for idx, (i, r) in enumerate(zip(range(len(series_results[:15])), series_results[:15])):
                target = test_dates[i].strftime('%Y-%m-%d')
                real = r.get('date', '')
                value = r.get('value', '')
                status = r.get('status', '')
                f.write(f"| {idx+1} | {target} | {real} | {value} | {status} |\n")
            f.write("\n")

    logger.info(f"💾 Reporte markdown guardado: {md_file}")

    return csv_file

def main():
    parser = argparse.ArgumentParser(description="Test FRED historical data samples")
    parser.add_argument('--api-key', required=True, help='FRED API key')
    parser.add_argument('--samples', type=int, default=20, help='Número de muestras aleatorias')
    parser.add_argument('--output', type=str, default='data/fred_samples', help='Directorio de salida')

    args = parser.parse_args()

    # Ejecutar prueba
    results, test_dates = test_historical_samples(args.api_key, args.samples)

    # Analizar resultados
    analyze_results(results, test_dates)

    # Guardar reporte
    save_sample_report(results, test_dates, args.output)

    # Resumen final
    logger.info("\n" + "=" * 80)
    logger.info("✅ TEST COMPLETADO")
    logger.info("=" * 80)

    # Recomendaciones basadas en resultados
    logger.info("\n📋 RECOMENDACIONES PARA SNIPER V12:")

    # Análisis rápido de disponibilidad
    for series_key, series_results in results.items():
        success_rate = sum(1 for r in series_results if r['value'] is not None) / len(series_results) * 100
        if success_rate > 90:
            logger.info(f"   ✅ {series_key}: Alta disponibilidad ({success_rate:.1f}%)")
        elif success_rate > 70:
            logger.info(f"   ⚠️ {series_key}: Disponibilidad media ({success_rate:.1f}%)")
        else:
            logger.info(f"   ❌ {series_key}: Baja disponibilidad ({success_rate:.1f}%)")

if __name__ == '__main__':
    main()
