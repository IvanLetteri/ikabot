#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import gettext
import traceback
from ikabot.config import *
from ikabot.helpers.gui import *
from ikabot.helpers.botComm import *
from ikabot.helpers.pedirInfo import *
from ikabot.helpers.varios import esperar
from ikabot.helpers.process import forkear
from ikabot.helpers.varios import addPuntos
from ikabot.helpers.signals import setInfoSignal
from ikabot.helpers.recursos import getRecursosDisponibles

t = gettext.translation('entrenarTropas',
                        localedir,
                        languages=idiomas,
                        fallback=True)
_ = t.gettext

def getCuartelInfo(s, ciudad):
	params = {'view': 'barracks', 'cityId': ciudad['id'], 'position': ciudad['pos'], 'backgroundView': 'city', 'currentCityId': ciudad['id'], 'actionRequest': s.token(), 'ajax': '1'}
	data = s.post(params=params)
	return json.loads(data, strict=False)

def entrenar(s, ciudad, entrenamiento):
	payload = {'action': 'CityScreen', 'function': 'buildUnits', 'actionRequest': s.token(), 'cityId': ciudad['id'], 'position': ciudad['pos'], 'backgroundView': 'city', 'currentCityId': ciudad['id'], 'templateView': 'barracks', 'ajax': '1'}
	for tropa in entrenamiento:
		payload[ tropa['unit_type_id'] ] = tropa['entrenar']
	s.post(payloadPost=payload)

def esperarEntrenamiento(s, ciudad):
	data = getCuartelInfo(s, ciudad)
	html = data[1][1][1]
	segundos = re.search(r'\'buildProgress\', (\d+),', html)
	if segundos:
		segundos = segundos.group(1)
		segundos = segundos - data[0][1]['time']
		esperar(segundos + 5)

def getCiudadanosDisponibles(html):
	ciudadanosDisp = re.search(r'js_GlobalMenu_citizens">(.*?)</span>', html).group(1)
	return int(ciudadanosDisp.replace(',', ''))

def planearEntrenamientos(s, ciudad, entrenamientos):
	while True:
		total = 0
		for entrenamiento in entrenamientos:
			for tropa in entrenamiento:
				total += tropa['cantidad']
		if total == 0:
			return

		for entrenamiento in entrenamientos:
			esperarEntrenamiento(s, ciudad)
			html = s.get(urlCiudad + ciudad['id'])
			ciudadanosDisp = getCiudadanosDisponibles(html)
			recursos = getRecursosDisponibles(html, num=True)
			maderaDisp  = recursos[0]
			vinoDisp    = recursos[1]
			marmolDisp  = recursos[2]
			cristalDisp = recursos[3]
			azufreDisp  = recursos[4]
			for tropa in entrenamiento:

				tropa['entrenar'] = tropa['cantidad']

				if 'wood' in tropa['costs']:
					limitante = maderaDisp // tropa['costs']['wood']
					if limitante < tropa['entrenar']:
						tropa['entrenar'] = limitante

				if 'wine' in tropa['costs']:
					limitante = vinoDisp // tropa['costs']['wine']
					if limitante < tropa['entrenar']:
						tropa['entrenar'] = limitante

				if 'marble' in ['costs']:
					limitante = marmolDisp // tropa['costs']['marble']
					if limitante < tropa['entrenar']:
						tropa['entrenar'] = limitante

				if 'cristal' in ['costs']:
					limitante = cristalDisp // tropa['costs']['cristal']
					if limitante < tropa['entrenar']:
						tropa['entrenar'] = limitante

				if 'sulfur' in tropa['costs']:
					limitante = azufreDisp // tropa['costs']['sulfur']
					if limitante < tropa['entrenar']:
						tropa['entrenar'] = limitante

				if 'citizens' in tropa['costs']:
					limitante = ciudadanosDisp // tropa['costs']['citizens']
					if limitante < tropa['entrenar']:
						tropa['entrenar'] = limitante

				if 'wood' in tropa['costs']:
					maderaDisp -= tropa['costs']['wood'] * tropa['entrenar']
				if 'wine' in tropa['costs']:
					vinoDisp -= tropa['costs']['wine'] * tropa['entrenar']
				if 'marble' in tropa['costs']:
					marmolDisp -= tropa['costs']['marble'] * tropa['entrenar']
				if 'cristal' in ['costs']:
					cristalDisp -= tropa['costs']['cristal'] * tropa['entrenar']
				if 'sulfur' in tropa['costs']:
					azufreDisp -= tropa['costs']['sulfur'] * tropa['entrenar']
				if 'citizens' in tropa['costs']:
					ciudadanosDisp -= tropa['costs']['citizens'] * tropa['entrenar']

				tropa['cantidad'] -= tropa['entrenar']

			total = 0
			for tropa in entrenamiento:
				total += tropa['entrenar']
			if total == 0:
				msg = 'No se pudo terminar de entrenar tropas por falta de recursos.'
				sendToBot(msg)
				return
			entrenar(s, ciudad, entrenamiento)

def entrenarTropas(s):
	banner()
	print('¿En qué ciudad quiere entrenar las tropas?')
	ciudad = elegirCiudad(s)
	for i in range(len(ciudad['position'])):
		if ciudad['position'][i]['building'] == 'barracks':
			ciudad['pos'] = str(i)
			break

	data = getCuartelInfo(s, ciudad)
	unidades_info = data[2][1]

	banner()
	i = 1
	unidades = []
	maxSize = 0
	while 'js_barracksSlider{:d}'.format(i) in unidades_info:
		# {"identifier":"phalanx","unit_type_id":303,"costs":{"citizens":1,"wood":27,"sulfur":30,"upkeep":3,"completiontime":71.169695412658},"local_name":"Hoplita"}
		info = unidades_info['js_barracksSlider{:d}'.format(i)]['slider']['control_data']
		info = json.loads(info, strict=False)
		if maxSize < len(info['local_name']):
			maxSize = len(info['local_name'])
		unidades.append(info)
		i += 1

	entrenamientos = []
	while True:
		print('Entrenar:')
		for unidad in unidades:
			cantidad = read(msg='{}{}:'.format(' '*(maxSize-len(unidad['local_name'])), unidad['local_name']), min=0, empty=True)
			if cantidad == '':
				cantidad = 0
			unidad['cantidad'] = cantidad

		print('\nCosto total:')
		costo = {'ciudadanos': 0, 'madera': 0, 'azufre': 0}
		for unidad in unidades:
			costo['ciudadanos'] += unidad['costs']['citizens'] * unidad['cantidad']
			costo['madera'] += unidad['costs']['wood'] * unidad['cantidad']
			if 'sulfur' in unidad['costs']:
				costo['azufre'] += unidad['costs']['sulfur'] * unidad['cantidad']
		print('Ciudadanos: {}'.format(addPuntos(costo['ciudadanos'])))
		print('    Madera: {}'.format(addPuntos(costo['madera'])))
		print('    Azufre: {}'.format(addPuntos(costo['azufre'])))

		print('\nProceder? [Y/n]')
		rta = read(values=['y', 'Y', 'n', 'N', ''])
		if rta.lower() == 'n':
			return

		entrenamientos.append(unidades)

		print('\n¿Quiere entrenar más tropas al terminar? [y/N]')
		rta = read(values=['y', 'Y', 'n', 'N', ''])
		if rta.lower() == 'y':
			print('')
			continue
		else:
			break

	print('\nSe entrenarán las tropas seleccionadas.')
	enter()

	forkear(s)
	if s.padre is True:
		return

	info = '\nEntreno tropas en {}\n'.format(ciudad['cityName'])
	setInfoSignal(s, info)
	try:
		planearEntrenamientos(s, ciudad, entrenamientos)
	except:
		msg = 'Error en:\n{}\nCausa:\n{}'.format(info, traceback.format_exc())
		sendToBot(msg)
	finally:
		s.logout()
