import httpx
import pytest
import respx

from lambda_weather_air_archiver import gios, imgw, openmeteo
from lambda_weather_air_archiver.config import (
    GIOS_AIR_QUALITY_INDEX,
    GIOS_ALL_STATIONS,
    GIOS_SENSOR_DATA,
    GIOS_SENSORS,
    IMGW_METEO_DATA,
    IMGW_SYNOPTIC_DATA,
    OPEN_METEO_AIR_QUALITY_URL,
    OPEN_METEO_FORECAST_URL,
)
from lambda_weather_air_archiver.gios import (
    StationsNotFoundError,
    get_gios_data,
    get_gios_stations,
)
from lambda_weather_air_archiver.imgw import (
    get_imgw_data,
    get_imgw_meteo_data,
    get_imgw_stations,
)
from lambda_weather_air_archiver.models import (
    GiosFields,
    GiosSensorFields,
    GiosSensorReadingFields,
    GiosSnapshot,
    ImgwMeteoFields,
    ImgwSnapshot,
    ImgwStation,
    OpenMeteoAirQualityVariables,
    OpenMeteoSnapshot,
)
from lambda_weather_air_archiver.openmeteo import get_open_meteo_data

TEST_CITY = "Wrocław"
LATITUDE = 51.107885
LONGITUDE = 17.038538

Snapshot = GiosSnapshot | ImgwSnapshot | OpenMeteoSnapshot

def _gios_station(station_id: int, city: str) -> dict[str, int | str]:
    return {
        GiosFields.ID: station_id,
        GiosFields.CODE: f"STATION-{station_id}",
        GiosFields.CITY: city,
    }

def _gios_page(stations: list[dict[str, int | str]], total_pages: int = 1) -> dict:
    return {"totalPages": total_pages, GiosFields.STATIONS: stations}

def _imgw_station(station_id: int, city: str) -> dict[str, int | str]:
    return {
            ImgwMeteoFields.CODE: station_id,
            ImgwMeteoFields.NAME: city,
        }

def _imgw_meteo_reading() -> dict[str, float | None]:
    return {field: None for field in ImgwMeteoFields}

def _open_meteo_air() -> dict:
    return {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "elevation": 120,
        "hourly": {"time": [1762160400], **{variable: [1.0] for variable in OpenMeteoAirQualityVariables}},
        "current": {"time": 1762160400, **{variable: 1.0 for variable in OpenMeteoAirQualityVariables}},
    }

@pytest.fixture
def saved_snapshots(monkeypatch: pytest.MonkeyPatch) -> list[Snapshot]:
    saved: list[Snapshot] = []

    def fake_save(data: Snapshot) -> None:
        saved.append(data)

    for module in (gios, imgw, openmeteo):
        monkeypatch.setattr(module, "save_to_json", fake_save)
    return saved

@respx.mock
def test_gios_stations_filtered_by_city():
    page = {
        "totalPages": 1,
        GiosFields.STATIONS: [
            _gios_station(1, "WROCŁAW"),
            _gios_station(2, "Kraków"),
            _gios_station(3, "wrocław"),
        ],
    }
    respx.get(GIOS_ALL_STATIONS).mock(return_value=httpx.Response(200, json=page))

    with httpx.Client(timeout=30) as client:
        stations = get_gios_stations(client=client, city=TEST_CITY)

    assert [station.id for station in stations] == [1, 3]

@respx.mock
def test_gios_stations_collected_from_all_pages():
    respx.get(GIOS_ALL_STATIONS).mock(side_effect=[
        httpx.Response(200, json=_gios_page([_gios_station(1, TEST_CITY)], total_pages=2)),
        httpx.Response(200, json=_gios_page([_gios_station(2, TEST_CITY)], total_pages=2)),
    ])

    with httpx.Client(timeout=30) as client:
        stations = get_gios_stations(client=client, city=TEST_CITY)

    assert [station.id for station in stations] == [1, 2]

@respx.mock
def test_gios_failing_sensor_does_not_stop_others(saved_snapshots):
    sensors = {
        GiosSensorFields.MEASURMENT_STATIONS: [
            {GiosSensorFields.INDICATOR_ID: 10, GiosSensorFields.INDICATOR_CODE: "PM10"},
            {GiosSensorFields.INDICATOR_ID: 20, GiosSensorFields.INDICATOR_CODE: "NO2"},
        ]
    }
    readings = {
        GiosSensorReadingFields.MEASURMENTS: [
            {GiosSensorReadingFields.DATE: "2026-11-03 10:00:00", GiosSensorReadingFields.VALUE: 12.5},
        ]
    }
    respx.get(GIOS_ALL_STATIONS).mock(return_value=httpx.Response(200, json=_gios_page([_gios_station(1, TEST_CITY)])))
    respx.get(GIOS_SENSORS + "1").mock(return_value=httpx.Response(200, json=sensors))
    respx.get(GIOS_SENSOR_DATA + "10").mock(return_value=httpx.Response(400, json={"error_reason": "manual"}))
    respx.get(GIOS_SENSOR_DATA + "20").mock(return_value=httpx.Response(200, json=readings))
    respx.get(GIOS_AIR_QUALITY_INDEX + "1").mock(return_value=httpx.Response(400))

    get_gios_data(TEST_CITY)

    station = saved_snapshots[0].stations[0]
    sensor_readings = {sensor.id: sensor.readings for sensor in station.sensors}
    assert sensor_readings[10] == []
    assert len(sensor_readings[20]) == 1

@respx.mock
def test_gios_no_stations_raises():
    respx.get(GIOS_ALL_STATIONS).mock(return_value=httpx.Response(200, json=_gios_page([_gios_station(1, "Kraków")])))

    with pytest.raises(StationsNotFoundError):
        get_gios_data(TEST_CITY)

@respx.mock
def test_imgw_stations_filtered_by_city():

    stations = [
        _imgw_station(1, "WROCŁAW"),
        _imgw_station(2, "Kraków"),
        _imgw_station(3, "wrocław"),
    ]

    respx.get(IMGW_METEO_DATA).mock(return_value=httpx.Response(200, json=stations))

    with httpx.Client(timeout=30) as client:
        stations = get_imgw_stations(client=client,url=IMGW_METEO_DATA, name_field=ImgwMeteoFields.NAME, city=TEST_CITY)

    assert [station.id for station in stations] == [1, 3]

@respx.mock
def test_imgw_empty_meteo_response_returns_none():
    station = ImgwStation.model_validate(_imgw_station(1, TEST_CITY))
    respx.get(IMGW_METEO_DATA + "1").mock(return_value=httpx.Response(200, json=[]))

    with httpx.Client(timeout=30) as client:
        assert get_imgw_meteo_data(client=client, station=station) is None

@respx.mock
def test_imgw_bad_reading_does_not_stop_others(saved_snapshots):
    bad_reading = _imgw_meteo_reading() | {ImgwMeteoFields.AVG_WIND_SPEED: -1}
    respx.get(IMGW_METEO_DATA).mock(return_value=httpx.Response(200, json=[
        _imgw_station(1, TEST_CITY),
        _imgw_station(2, TEST_CITY),
    ]))
    respx.get(IMGW_SYNOPTIC_DATA).mock(return_value=httpx.Response(200, json=[]))
    respx.get(IMGW_METEO_DATA + "1").mock(return_value=httpx.Response(200, json=[bad_reading]))
    respx.get(IMGW_METEO_DATA + "2").mock(return_value=httpx.Response(200, json=[_imgw_meteo_reading()]))

    get_imgw_data(TEST_CITY)

    readings = {station.id: station.reading for station in saved_snapshots[0].meteo_stations}
    assert readings[1] is None
    assert readings[2] is not None

@respx.mock
def test_openmeteo_failed_weather_still_saves_air(saved_snapshots):
    respx.get(OPEN_METEO_FORECAST_URL).mock(return_value=httpx.Response(200, json={}))
    respx.get(OPEN_METEO_AIR_QUALITY_URL).mock(return_value=httpx.Response(200, json=_open_meteo_air()))

    get_open_meteo_data(LATITUDE, LONGITUDE)

    snapshot = saved_snapshots[0]
    assert snapshot.weather is None
    assert snapshot.air_quality is not None
