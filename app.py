import collections
import json
import pathlib

import pandas
import streamlit as st


def main():
    # ui - page
    st.set_page_config(
        page_title=f'Petrol Book',
        page_icon=':oncoming_automobile:',
        layout='wide',
        initial_sidebar_state='expanded',
    )

    # ui - sidebar
    pb_file = st.text_input(
        label='petrol-book file',
        value='',
    )

    pb_path = pathlib.Path(pb_file)
    if not pb_path.exists():
        st.warning('please check your path or new file will created')
        content = {
            'fuelingOperations': [],
            'meta': {
                'manufacturer': '',
                'model': ''
            },
            'units': {
                'costs': '\u20ac',
                'distance': 'km',
                'liquid': 'l'
            }
        }

    else:
        content = read_petrol_book(pb_file)

    manufacturer = st.sidebar.text_input(label='manufacturer', value=content['meta']['manufacturer'])
    model = st.sidebar.text_input(label='model', value=content['meta']['model'])
    u_costs = st.sidebar.text_input(label='costs', value=content['units']['costs'])
    u_distance = st.sidebar.text_input(label='distance', value=content['units']['distance'])
    u_liquid = st.sidebar.text_input(label='liquid', value=content['units']['liquid'])
    calc_distance = int(st.sidebar.text_input(label='calc_distance', value=100))

    if manufacturer == '':
        st.error('please enter manufacturer')
        st.stop()
    content['meta']['manufacturer'] = manufacturer

    if model == '':
        st.error('please enter model')
        st.stop()
    content['meta']['model'] = model

    # ui - main
    all_ps = [x['petrolStation'] for x in content['fuelingOperations']]
    c = collections.Counter(all_ps)
    cols = st.columns([1, 1, 2, 2, 1, 1, 1, 1, 1])
    dti = cols[0].date_input(label='date', format='YYYY-MM-DD')
    tti = cols[1].time_input(label='time', step=60)
    psi = cols[2].text_input(
        label='petrolStation',
        key='petrolStation',
        on_change=petrol_station_complete,
        args=[c]
    )
    pti = cols[3].selectbox(label='petrolType', options=['Super E5', 'Super E10', 'Super Plus E5', ])
    ci = cols[4].number_input(label='costs', min_value=0.0)
    li = cols[5].number_input(label='liquid', min_value=0.0)
    di = cols[6].number_input(label='distance', min_value=0.0)
    mi = cols[7].number_input(label='mileage', min_value=0)
    ai = cols[8].button(label='add')
    if ai:
        if ci == 0:
            st.error('costs can not be zero')
            st.stop()

        if li == 0:
            st.error('liquid can not be zero')
            st.stop()

        if di == 0:
            st.error('distance can not be zero')
            st.stop()

        with st.spinner('ai pressed'):
            content['fuelingOperations'].append({
                'date': dti.strftime('%Y-%m-%d'),
                'time': tti.strftime('%H:%M'),
                'petrolStation': psi,
                'petrolType': pti,
                'costs': ci,
                'liquid': li,
                'distance': di,
                'mileage': mi,
                'units': {
                    'costs': u_costs,
                    'distance': u_distance,
                    'liquid': u_liquid
                }
            })
            with pathlib.Path(pb_file).open('w', encoding='UTF-8') as fh:
                json.dump(content, fh, indent=2)
            st.rerun()

    if not content['fuelingOperations']:
        st.error('please add fuelings')
        st.stop()

    data = []
    start_ma = content['fuelingOperations'][0]['mileage'] - content['fuelingOperations'][0]['distance']
    for i in content['fuelingOperations']:
        if i['liquid'] is None:
            tmp = {}
            for v in i:
                if i[v] == '' or i[v] is None or v == 'units':
                    continue
                if v == 'costs':
                    tmp[v] = f"{i[v]} {i['units']['costs']}"
                elif v == 'liquid':
                    tmp[v] = f"{i[v]} {i['units']['liquid']}"
                elif v == 'distance':
                    tmp[v] = f"{i[v]} {i['units']['distance']}"
                elif v == 'mileage':
                    tmp[v] = f"{i[v]} {i['units']['distance']}"
                else:
                    tmp[v] = i[v]
            data.append(tmp)
        else:
            data.append({
                'date': i['date'],
                'time': i['time'],
                'petrolStation': i['petrolStation'],
                'petrolType': i['petrolType'],
                'costs': f"{i['costs']} {i['units']['costs']}",
                'liquid': f"{i['liquid']} {i['units']['liquid']}",
                'distance': f"{i['distance']} {i['units']['distance']}",
                'mileage': f"{i['mileage'] - start_ma} {i['units']['distance']}",
                'costs / liquid': f"{round(i['costs'] / i['liquid'], 3)} {i['units']['costs']} / {i['units']['liquid']}",
                f'liquid / {calc_distance} distance': f"{round((i['liquid'] / i['distance']) * calc_distance, 2)} {i['units']['liquid']} / {calc_distance}{i['units']['distance']}",
                f'costs / {calc_distance} distance': f"{round((i['costs'] / i['distance']) * calc_distance, 2)} {i['units']['costs']} / {calc_distance}{i['units']['distance']}"
            })

    df = pandas.DataFrame(data)
    st.dataframe(
        data=df.sort_values(by=['date'], ascending=False),
        height=900,
        use_container_width=True,
        hide_index=True
    )


@st.cache_data
def read_petrol_book(pb_file: str) -> dict:
    if pb_file == '':
        st.error('please enter petrol-book file')
        st.stop()
    pb_path = pathlib.Path(pb_file)
    with pb_path.open(encoding='UTF-8') as source:
        return json.load(source)


def petrol_station_complete(counter: collections.Counter) -> None:
    for c in counter:
        if st.session_state.petrolStation in c.lower():
            st.session_state.petrolStation = c


if __name__ == '__main__':
    main()
