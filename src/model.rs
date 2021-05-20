use std::{fs::{File, OpenOptions}, io::{BufReader, Write}};

use liquidfun::box2d::common::math::*;
use liquidfun::box2d::particle::*;
use liquidfun::box2d::dynamics::body::*;
use liquidfun::box2d::collision::shapes::polygon_shape::PolygonShape;
use liquidfun::box2d::particle::particle_system::*;
use liquidfun::box2d::dynamics::world::*;

use serde::Deserialize;

const DPI: f32 = 8.0;

const SCALE: f32 = 0.05;
const MARGIN: f32 = 3.0;
const EXTRA: f32 = 1.0;
const SEG_WIDTH: f32 = 2.2;

pub struct Model {
    pub world: World,
    pub particle_system: ParticleSystem,

    pub drawwalls: bool,
    pub finished: bool,

    pub width: usize,
    pub height: usize,
    pub cwidth: usize,
    pub cheight: usize,

    points: Vec<Vec<f32>>,
    special: Body,
    bar: Body,
    frames: File,
}

#[derive(Deserialize)]
struct Properties {
    size: Vec<usize>,
    segments: Vec<Vec<Vec<f32>>>,
    special: Vec<f32>,
    points: Vec<Vec<f32>>,
    compile: Vec<usize>,
}

fn create_body(world: &mut World, x: f32, y: f32, w: f32, h: f32, rot: f32) -> Body {
    // Define the ground body.
	let mut ground_body_def = BodyDef::default();
	ground_body_def.position.set(x, y);
    ground_body_def.angle = rot;
	// Call the body factory which allocates memory for the ground body
	let ground_body = world.create_body(&ground_body_def);
	// Define the ground box shape.
	let mut ground_box = PolygonShape::new();
	// The extents are the half-widths of the box.
	ground_box.set_as_box(w, h);
	// Add the ground fixture to the ground body.
	ground_body.create_fixture_from_shape(&ground_box, 0.0);

    ground_body
}

impl Default for Model {
    fn default() -> Self {
        let file = File::open("segments.json").map_err(|e| format!("Could not open segments.json: {}", e)).unwrap();
        let reader = BufReader::new(file);
        let properties: Properties = serde_json::from_reader(reader).unwrap();
        let gravity = Vec2::new(0.0, -10.0);

        let mut world = World::new(&gravity);

        let mut particle_system_def = ParticleSystemDef::default();
        particle_system_def.radius = 0.07;

        let particle_system = world.create_particle_system(&particle_system_def);

        let halfh = (properties.size[0] as f32) / 2.0 * SCALE;
        let halfw = (properties.size[1] as f32) / 2.0 * SCALE;

        // Create the three walls on the dges of the simulation (left, right, and bottom)
        create_body(&mut world, 0.0, -halfh-EXTRA, 20.0+MARGIN, 0.1, 0.0);
        create_body(&mut world, halfw+MARGIN, 0.0, 0.1, 15.0+EXTRA, 0.0);
        create_body(&mut world, -halfw-MARGIN, 0.0, 0.1, 15.0+EXTRA, 0.0);

        // Draw the octopus
        for path in properties.segments {
            for obj in path {
                let x = obj[2]*SCALE - halfw;
                let y = obj[3]*SCALE - halfh;
                create_body(&mut world, x, y, (obj[1]/2.0+SEG_WIDTH)*SCALE, SEG_WIDTH*SCALE, obj[4]);
            }
        }

        // Create the two edges on the bottom of the octopus that will be removed to let the water spill
        let sp = properties.special;
        let special = create_body(&mut world, sp[1]*SCALE, sp[2]*SCALE,
                                  sp[0]/2.0*SCALE + SEG_WIDTH*SCALE, SEG_WIDTH*SCALE, sp[3]);
        let bar = create_body(&mut world, 0.0, -9.0, 20.0+MARGIN, 0.1, 0.0);

        let frames = OpenOptions::new().read(true).write(true).create(true)
            .open("frames-rust.bin").unwrap();

        Model {
            world, particle_system, special, bar, frames,

            points: properties.points,
            width: properties.size[1],
            height: properties.size[0],
            cwidth: properties.compile[1],
            cheight: properties.compile[0],
            drawwalls: true,
            finished: false,
        }
    }
}

impl Model {
    pub fn update(&mut self, t: i32) {
        // I don't think the choice of this makes a difference.
        // self.world.step(1.0/60.0, 2, 1);
        self.world.step(1.0/60.0, 8, 3);

        if t % 100 == 0 {
            println!("frame {}", t);
        }

        // From t=0 to t=1000, fill the octopus with particles every 100 timesteps
        if t % 100 == 0 && t <= 1000 {
            for p in &self.points {
                let mut pd = ParticleDef::default();
                pd.flags = VISCOUS_PARTICLE;
                pd.position.set((p[0] as f32)*SCALE, (p[1] as f32)*SCALE);
                self.particle_system.create_particle(&pd);
            }
        }

        // From t=1100 to t=2000, place particles on the ground underneath the octopus
        if t % 100 == 0 && t >= 1100 && t <= 2000 {
            let mut x = -15.0;
            while x < 15.0 {
                let mut y = -8.5;
                while y < -6.5 {
                    let mut pd = ParticleDef::default();
                    pd.flags = POWDER_PARTICLE;
                    // this was supposed to do fancy surface tension effects, but it just made things worse
                    // if t == 2000 {
                        // pd.flags = pd.flags | TENSILE_PARTICLE;
                    // }
                    pd.position.set(x, y);
                    self.particle_system.create_particle(&pd);
                    y += 1.0/DPI;
                }
                x += 1.0/DPI;
            }
        }

        // From t=2400 to t=4275, release particles and record frames
        if t > 2400 {
            self.drawwalls = false;
            self.world.destroy_body(&mut self.bar);
            self.world.destroy_body(&mut self.special);
            if t <= 2400+625*3 {
                self.frames.write_all(&self.compile(self.cwidth, self.cheight)).unwrap();
            } else {
                self.finished = true;
                println!("Compiled all frames! Goodbye!");
            }
        }
    }

    // Store all particle positions as a bitmap image with an astounding 1 bit of color
    // (ie storing pixels as on or off) The image bits are encoded into bytes in little-endian.
    fn compile(&self, width: usize, height: usize) -> Vec<u8> {
        let mut buffer = vec![0; width*height/8];
        for p in self.particle_system.get_position_buffer() {
            let xf = (p.x/SCALE / (self.width as f32) + 0.5) * (width as f32);
            let yf = (p.y/SCALE / (self.height as f32) + 0.5) * (height as f32);
            let xi = (xf  + 0.5) as i32;
            let yi = (height as i32) - ((yf + 0.5) as i32);

            if xi < 0 || yi < 0 || xi >= (width as i32) || yi >= (height as i32) {
                continue;
            }

            let x = xi as usize;
            let y = yi as usize;
            buffer[y*width/8 + x/8] |= 1 << (x % 8);
        }
        buffer
    }
}
