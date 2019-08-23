from math import atan2, ceil, cos, sin
from random import choice, randint, uniform
from time import sleep, time
from typing import Set
import os
import pygame


def fire_artillery():
	objects.add(Shell(random_bottom_pixel(), fuzz_position(pygame.mouse.get_pos()), shell_damage, shell_speed))


def fuzz_position(pos: (int, int), amt: int = 50) -> (int, int):
	x, y = pos
	x += randint(-amt, amt)
	y += randint(-amt, amt)
	return x, y


def game_text(text: str, coords: (int, int) = (0, 0), size: int = 12):
	text = text.replace('\t', ' '*4)
	myfont = pygame.font.SysFont('Consolas', size)
	for i, line in enumerate(text.split('\n')):
		textsurface = myfont.render(line, True, white)
		x, y = coords
		y += i*size
		screen.blit(textsurface, (x, y))


def get_files_with_extension(location: str, extension: str) -> Set[str]:
	extension = '.' + extension
	filenames = set()
	for file in os.listdir(location):
		if file.endswith(extension):
			filenames.add(location+'/'+file)
	return filenames


def leave():
	pygame.display.quit()
	pygame.quit()
	exit()


def progress_bar(fraction: float, coords: (int, int), width: int = 100, height: int = 4):
	# red bg
	pygame.draw.rect(screen, (255, 0, 0), coords+(width, height))
	# green fg
	pygame.draw.rect(screen, (0, 255, 0), coords+(int(fraction*width), height))


def random_airship_image() -> pygame.Surface:
	airship_image_filenames = get_files_with_extension('img/airship', 'png')
	filename = choice(list(airship_image_filenames))
	return pygame.image.load(filename)


def random_bottom_pixel() -> (int, int):
	x = randint(0, screen.get_width())
	y = screen.get_height()
	return x, y


def random_left_pixel() -> (int, int):
	x = randint(-200, -100)
	y = randint(0, screen.get_height()-100)
	return x, y


def sfx(category: str):
	filename = choice(list(get_files_with_extension('sfx/'+category, 'wav')))
	try:
		pygame.mixer.find_channel().queue(pygame.mixer.Sound(filename))
	except AttributeError:
		pass


class Shell:
	def __init__(self, source: (int, int), destination: (int, int), speed: int, base_damage: int):
		self.position = source
		self.destination = destination
		self.speed = speed
		self.base_damage = base_damage

	# properties
	@property
	def burst_corners(self) -> ((int, int), (int, int), (int, int), (int, int)):
		ulhc = self.position[0] - self.burst_radius, self.position[1] - self.burst_radius
		urhc = self.position[0] + self.burst_radius, self.position[1] - self.burst_radius
		blhc = self.position[0] - self.burst_radius, self.position[1] + self.burst_radius
		brhc = self.position[0] + self.burst_radius, self.position[1] + self.burst_radius
		return ulhc, urhc, blhc, brhc

	@property
	def burst_radius(self) -> int:
		r = 0
		v = burst_radius_velocity
		while 0 < v:
			r += v
			v -= burst_radius_deceleration
		return r

	@property
	def damage(self) -> int:
		return round(uniform(.5, 1.5) * self.base_damage)

	@property
	def delta(self) -> (int, int):
		return tuple(self.position[i] - self.destination[i] for i in range(2))

	@property
	def dist(self) -> float:
		dx, dy = self.delta
		return (dx**2 + dy**2)**.5

	@property
	def onscreen(self) -> bool:
		x, y = self.position
		sx, sy = screen.get_size()
		return 0 <= x <= sx and 0 <= y <= sy

	@property
	def theta(self) -> float:
		dx, dy = self.delta
		return atan2(dy, dx)

	@property
	def vxy(self) -> (float, float):
		theta = self.theta
		return -self.speed*cos(theta), -self.speed*sin(theta)

	# methods
	def detonate(self):
		for airship in {i for i in objects if isinstance(i, Airship)}:
			# direct hit
			if airship.includes(self.position):
				airship.hit(self.damage)
			# indirect hit
			elif any(airship.includes(i) for i in self.burst_corners):
				airship.hit(self.damage//2)
		objects.remove(self)
		objects.add(Burst(self.position))
		sfx('burst')
		del self

	def pos_in(self, ticks: int) -> (int, int):
		"""Get position of shell in n ticks"""
		x, y = self.position
		vx, vy = self.vxy
		x += round(ticks*vx)
		y += round(ticks*vy)
		return x, y

	def render(self):
		pygame.draw.aaline(screen, black, self.pos_in(-1), self.position)

	def tick(self):
		if self.dist < self.speed:
			return self.detonate()
		self.position = self.pos_in(1)
		# check if offscreen
		if not self.onscreen:
			objects.remove(self)
			del self


class Airship:
	def __init__(self, image: pygame.Surface, source: (int, int)):
		self.image = image
		self.position = source
		self.health = self.max_health

	# properties
	@property
	def area(self) -> int:
		x, y = self.image.get_size()
		return x*y

	@property
	def center(self) -> (int, int):
		x, y = self.position
		w, h = self.image.get_size()
		return int(x + w//2), int(y + w//2)

	@property
	def damage(self) -> int:
		return self.area // 50

	@property
	def max_health(self) -> int:
		return self.area // 100

	@property
	def speed(self) -> float:
		return 4000 / self.area * max(.5, self.health / self.max_health)

	# methods
	def die(self, kill_type: str = 'kill'):
		global health
		objects.remove(self)
		if kill_type == 'win':
			health -= self.damage
		elif kill_type == 'crash':
			objects.add(Burst(self.center))
			sfx('crash')
		del self

	def hit(self, damage: int):
		global score
		self.health -= damage
		if self.health <= 0:
			score += self.max_health
			self.die()

	def includes(self, coords: (int, int)) -> bool:
		x, y = coords
		xmin, ymin = self.position
		xmax, ymax = xmin+self.image.get_width(), ymin+self.image.get_height()
		return xmin <= x <= xmax and ymin <= y <= ymax

	def render(self):
		screen.blit(self.image, self.position)
		x, y = self.position
		# HP bar
		y += self.image.get_height()
		progress_bar(self.health/self.max_health, (x, y), self.image.get_width())
		# HP
		y += 4
		game_text('HP: {}/{}'.format(self.health, self.max_health), (x, y))
		# todo taunts

	def tick(self):
		x, y = self.position
		x += self.speed
		if 3 * self.health < self.max_health:
			y += 1
		self.position = x, y
		# did it win?
		if screen.get_width() < self.position[0]:
			self.die('win')
		# did it fall?
		elif screen.get_height() < self.center[1]:
			self.die('crash')


class Burst:
	def __init__(self, position: (int, int)):
		self.position = position
		self.radius = 0
		self.radius_velocity = burst_radius_velocity
		self.t = 0

	@property
	def alpha(self) -> int:
		return max(0, 255 - self.t * 255 // (2 * target_fps)) # 60 frames = 2 sec

	@property
	def color(self) -> (int, int, int):
		# goal: white -> yellow -> orange -> red -> black
		colors = [ # need TWELVE keys
			(255, 255, 255), # white
			(255, 255, 128),
			(255, 255, 0), # yellow
			(255, 192, 0),
			(255, 128, 0), # orange
			(255, 64, 0),
			(255, 0, 0), # red
			(192, 0, 0),
			(128, 0, 0), # dark red
			(64, 0, 0),
		]
		# return 255, 255 - 255//11 * self.t, max(0, 255 - 255//5 * self.t)
		return colors[self.t] if self.t < len(colors) - 1 else black

	def render(self):
		# pygame.draw.circle(screen, self.color, self.position, self.radius)
		burst_surface = pygame.Surface((self.radius*2,)*2, pygame.SRCALPHA)
		pygame.draw.circle(burst_surface, self.color+(self.alpha,), (self.radius,)*2, self.radius)
		x, y = self.position
		x -= self.radius
		y -= self.radius
		screen.blit(burst_surface, (x, y))

	def tick(self):
		self.radius += self.radius_velocity
		if self.radius_velocity:
			self.radius_velocity -= burst_radius_deceleration
		self.t += 1
		if self.radius < 0:
			objects.remove(self)
			del self


# do not touch these variables after game start
black = (0,)*3
white = (255,)*3
refresh = pygame.display.flip
target_fps = 30

artillery_timeout = .3
burst_radius_deceleration = 5
burst_radius_velocity = 10
shell_damage = 10
shell_speed = 10
# touch these idgaf
pygame.init()
pygame.mixer.init()
pygame.mixer.music.load('sfx/airraid.wav')
pygame.mixer.music.play(-1)
pygame.mixer.set_num_channels(16)
screen = pygame.display.set_mode((1000, 500), pygame.RESIZABLE) # type: pygame.Surface

current_timeout = 0
health = 1000
objects = set() # type: set
paused = False
score = 0

while 0 < health: # main loop
	# todo badges, upgrades
	start_time = time()
	airship_list = [i for i in objects if isinstance(i, Airship)]
	max_airships = ceil(score**.5 / 10)
	# render
	screen.fill((0, 128, 255))
	sorted_objects = airship_list + [i for i in objects if not isinstance(i, Airship)]
	for obj in sorted_objects:
		obj.render()
	game_text('Score: {}\nHP: {}\nLevel: {}'.format(score, health, max_airships), (0, 0), 24)
	refresh()
	# check for keypresses
	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			leave()
		elif event.type == pygame.KEYDOWN:
			if event.key == pygame.K_ESCAPE:
				leave()
			elif event.key == pygame.K_p:
				paused = not paused
		elif event.type == pygame.VIDEORESIZE:
			pygame.display.set_mode(event.size, pygame.RESIZABLE)
	# fire!
	if pygame.mouse.get_pressed()[0] and not current_timeout:
		fire_artillery()
		current_timeout = artillery_timeout
	# only do next ones if unpaused
	if paused:
		continue
	# simulate existing objects
	for obj in {i for i in objects}:
		obj.tick()
	# spawn new airships at random left side
	if len(airship_list) <= max_airships:
		objects.add(Airship(random_airship_image(), random_left_pixel()))
	# airships damage you at right side
	remaining_time = 1/target_fps - (time() - start_time)
	if 0 < remaining_time:
		sleep(remaining_time)
	# fire timeout
	if current_timeout:
		if 1/target_fps < current_timeout:
			current_timeout -= 1/target_fps
		else:
			current_timeout = 0
print('Thank you for playing AirRaid by Mocha!\nFinal Score: {}'.format(score))
input()
